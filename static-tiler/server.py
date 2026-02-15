import logging
import os
import signal
import sys
import time
from typing import Dict, List, Optional

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst

logger = logging.getLogger(__name__)


class StaticTiler:
    """
    Static tiler that takes N inputs (tile slots) and M apphosts (video sources).
    Each input slot has an inputselector that can choose from any of the M apphost streams.
    Pipeline: inputselectors -> queues -> nvvideoconvert (upload to GPU) -> nvstreammux ->
              nvmultistreamtiler -> nvv4l2h264enc -> h264parse -> tcpserversink
    """

    def __init__(
        self, num_inputs: int, num_apphosts: int, grid_cols: int, grid_rows: int
    ):
        """
        Initialize the static tiler.

        Args:
            num_inputs: Number of tile slots (N) - must equal grid_cols * grid_rows
            num_apphosts: Number of apphost sources (M) - must be >= num_inputs
            grid_cols: Number of columns in the tiler grid
            grid_rows: Number of rows in the tiler grid
        """
        self.num_inputs = num_inputs
        self.num_apphosts = num_apphosts
        self.grid_cols = grid_cols
        self.grid_rows = grid_rows

        if num_inputs != grid_cols * grid_rows:
            raise ValueError(
                f"num_inputs ({num_inputs}) must equal grid_cols * grid_rows ({grid_cols * grid_rows})"
            )

        if num_apphosts < num_inputs:
            raise ValueError(
                f"num_apphosts ({num_apphosts}) must be >= num_inputs ({num_inputs})"
            )

        # Control signal mapping: which apphost feeds which input slot
        # Default: round-robin assignment
        self.input_assignments = [i % num_apphosts for i in range(num_inputs)]

        self.pipeline: Optional[Gst.Pipeline] = None
        self.loop: Optional[GLib.MainLoop] = None
        self.input_selectors: List[Gst.Element] = []

        logger.info(
            f"Initializing StaticTiler with {num_inputs} inputs, {num_apphosts} apphosts, {grid_cols}x{grid_rows} grid"
        )

    def set_input_assignment(self, slot_index: int, apphost_index: int):
        """
        Set which apphost feeds a particular input slot.

        Args:
            slot_index: The input slot (0 to N-1)
            apphost_index: The apphost source (0 to M-1)
        """
        if slot_index < 0 or slot_index >= self.num_inputs:
            logger.error(
                f"Invalid slot_index {slot_index}, must be 0-{self.num_inputs - 1}"
            )
            return

        if apphost_index < 0 or apphost_index >= self.num_apphosts:
            logger.error(
                f"Invalid apphost_index {apphost_index}, must be 0-{self.num_apphosts - 1}"
            )
            return

        self.input_assignments[slot_index] = apphost_index

        # If pipeline is running, switch the input selector
        if self.input_selectors and slot_index < len(self.input_selectors):
            selector = self.input_selectors[slot_index]
            # The active pad is the apphost_index pad
            sink_pads = list(selector.iterate_sink_pads())
            if apphost_index < len(sink_pads):
                selector.set_property("active-pad", sink_pads[apphost_index])
                logger.info(f"Switched slot {slot_index} to apphost {apphost_index}")

    def build_pipeline(self):
        """Build the GStreamer pipeline with input selectors and NVIDIA components."""
        logger.info("Building GStreamer pipeline...")

        # Initialize GStreamer
        Gst.init(None)

        # Create pipeline
        self.pipeline = Gst.Pipeline.new("static-tiler-pipeline")

        # Create nvstreammux
        streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
        if not streammux:
            logger.error(
                "Failed to create nvstreammux - ensure DeepStream is installed"
            )
            return False

        streammux.set_property("width", 1920)
        streammux.set_property("height", 1080)
        streammux.set_property("batch-size", self.num_inputs)
        streammux.set_property("batched-push-timeout", 40000)  # 40ms
        streammux.set_property("live-source", 1)

        # Create tiler
        tiler = Gst.ElementFactory.make("nvmultistreamtiler", "tiler")
        if not tiler:
            logger.error("Failed to create nvmultistreamtiler")
            return False

        tiler.set_property("rows", self.grid_rows)
        tiler.set_property("columns", self.grid_cols)
        tiler.set_property("width", 3840)
        tiler.set_property("height", 2160)

        # Create encoder
        encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
        if not encoder:
            logger.error("Failed to create nvv4l2h264enc")
            return False

        encoder.set_property("bitrate", 8000000)  # 8 Mbps
        encoder.set_property("control-rate", 1)  # Constant bitrate
        encoder.set_property("iframeinterval", 30)  # I-frame interval

        # Create h264parse
        h264parse = Gst.ElementFactory.make("h264parse", "h264-parser")
        if not h264parse:
            logger.error("Failed to create h264parse")
            return False

        # Create TCP server sink
        tcpsink = Gst.ElementFactory.make("tcpserversink", "tcp-sink")
        if not tcpsink:
            logger.error("Failed to create tcpserversink")
            return False

        tcpsink.set_property("host", "0.0.0.0")
        tcpsink.set_property("port", 6000)
        tcpsink.set_property("sync", False)

        # Add elements to pipeline
        self.pipeline.add(streammux)
        self.pipeline.add(tiler)
        self.pipeline.add(encoder)
        self.pipeline.add(h264parse)
        self.pipeline.add(tcpsink)

        # Link main pipeline elements
        if not streammux.link(tiler):
            logger.error("Failed to link streammux to tiler")
            return False

        if not tiler.link(encoder):
            logger.error("Failed to link tiler to encoder")
            return False

        if not encoder.link(h264parse):
            logger.error("Failed to link encoder to h264parse")
            return False

        if not h264parse.link(tcpsink):
            logger.error("Failed to link h264parse to tcpsink")
            return False

        # Build input selector branches for each input slot
        for slot_idx in range(self.num_inputs):
            # Create input selector for this slot
            selector = Gst.ElementFactory.make("input-selector", f"selector-{slot_idx}")
            if not selector:
                logger.error(f"Failed to create input-selector for slot {slot_idx}")
                return False

            self.input_selectors.append(selector)
            self.pipeline.add(selector)

            # Create queue after selector
            queue_post = Gst.ElementFactory.make(
                "queue", f"queue-post-selector-{slot_idx}"
            )
            if not queue_post:
                logger.error(
                    f"Failed to create post-selector queue for slot {slot_idx}"
                )
                return False

            queue_post.set_property("max-size-buffers", 10)
            queue_post.set_property("max-size-bytes", 0)
            queue_post.set_property("max-size-time", 0)

            self.pipeline.add(queue_post)

            # Create videoconvert to normalize format
            videoconv = Gst.ElementFactory.make("videoconvert", f"videoconv-{slot_idx}")
            if not videoconv:
                logger.error(f"Failed to create videoconvert for slot {slot_idx}")
                return False

            self.pipeline.add(videoconv)

            # Create videoscale to ensure proper dimensions
            videoscale = Gst.ElementFactory.make("videoscale", f"videoscale-{slot_idx}")
            if not videoscale:
                logger.error(f"Failed to create videoscale for slot {slot_idx}")
                return False

            self.pipeline.add(videoscale)

            # Create capsfilter for dimensions before GPU upload
            caps_cpu = Gst.Caps.from_string(
                "video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1"
            )
            capsfilter_cpu = Gst.ElementFactory.make(
                "capsfilter", f"capsfilter-cpu-{slot_idx}"
            )
            capsfilter_cpu.set_property("caps", caps_cpu)
            self.pipeline.add(capsfilter_cpu)

            # Create nvvideoconvert to upload to GPU
            nvvidconv = Gst.ElementFactory.make(
                "nvvideoconvert", f"nvvidconv-{slot_idx}"
            )
            if not nvvidconv:
                logger.error(f"Failed to create nvvideoconvert for slot {slot_idx}")
                return False

            self.pipeline.add(nvvidconv)

            # Create capsfilter for nvvideoconvert output
            # Use NV12 format for nvstreammux compatibility
            caps = Gst.Caps.from_string("video/x-raw(memory:NVMM),format=NV12")
            capsfilter = Gst.ElementFactory.make("capsfilter", f"capsfilter-{slot_idx}")
            capsfilter.set_property("caps", caps)
            self.pipeline.add(capsfilter)

            # Create queue between capsfilter and streammux
            queue_mux = Gst.ElementFactory.make("queue", f"queue-mux-{slot_idx}")
            if not queue_mux:
                logger.error(f"Failed to create mux queue for slot {slot_idx}")
                return False
            queue_mux.set_property("max-size-buffers", 10)
            self.pipeline.add(queue_mux)

            # Link: selector -> queue -> videoconvert -> videoscale -> capsfilter_cpu -> nvvideoconvert -> capsfilter -> queue -> streammux
            if not selector.link(queue_post):
                logger.error(f"Failed to link selector to queue for slot {slot_idx}")
                return False

            if not queue_post.link(videoconv):
                logger.error(
                    f"Failed to link queue to videoconvert for slot {slot_idx}"
                )
                return False

            if not videoconv.link(videoscale):
                logger.error(
                    f"Failed to link videoconvert to videoscale for slot {slot_idx}"
                )
                return False

            if not videoscale.link(capsfilter_cpu):
                logger.error(
                    f"Failed to link videoscale to capsfilter_cpu for slot {slot_idx}"
                )
                return False

            if not capsfilter_cpu.link(nvvidconv):
                logger.error(
                    f"Failed to link capsfilter_cpu to nvvideoconvert for slot {slot_idx}"
                )
                return False

            if not nvvidconv.link(capsfilter):
                logger.error(
                    f"Failed to link nvvideoconvert to capsfilter for slot {slot_idx}"
                )
                return False

            if not capsfilter.link(queue_mux):
                logger.error(
                    f"Failed to link capsfilter to queue_mux for slot {slot_idx}"
                )
                return False

            # Link queue_mux to streammux using link_pads with request pad
            sinkpad_name = f"sink_{slot_idx}"
            logger.info(
                f"Linking queue_mux to streammux pad {sinkpad_name} for slot {slot_idx}"
            )

            # Debug caps before linking
            queue_src_pad = queue_mux.get_static_pad("src")
            if queue_src_pad:
                logger.info(
                    f"Queue src pad template caps: {queue_src_pad.get_pad_template_caps()}"
                )

            if not queue_mux.link_pads("src", streammux, sinkpad_name):
                logger.error(
                    f"Failed to link queue_mux to streammux for slot {slot_idx}"
                )
                logger.error(
                    f"Streammux sink pad template: {streammux.get_pad_template('sink_%u')}"
                )
                return False

            logger.info(f"Successfully linked slot {slot_idx} to streammux")

            # Create source branches - one for each apphost feeding into this selector
            for apphost_idx in range(self.num_apphosts):
                # Construct FIFO path
                fifo_path = f"/dev/shm/apphost{apphost_idx + 1}/apphost{apphost_idx + 1}_video.fifo"

                # Create filesrc
                filesrc = Gst.ElementFactory.make(
                    "filesrc", f"filesrc-slot{slot_idx}-apphost{apphost_idx}"
                )
                if not filesrc:
                    logger.error(
                        f"Failed to create filesrc for slot {slot_idx}, apphost {apphost_idx}"
                    )
                    return False

                filesrc.set_property("location", fifo_path)

                # Create videoparse
                videoparse = Gst.ElementFactory.make(
                    "videoparse", f"videoparse-slot{slot_idx}-apphost{apphost_idx}"
                )
                if not videoparse:
                    logger.error(
                        f"Failed to create videoparse for slot {slot_idx}, apphost {apphost_idx}"
                    )
                    return False

                videoparse.set_property(
                    "format", 8
                )  # GST_VIDEO_FORMAT_RGBA (raw input from apphost)
                videoparse.set_property("width", 1920)
                videoparse.set_property("height", 1080)
                videoparse.set_property("framerate", "30/1")

                # Create queue before selector
                queue_pre = Gst.ElementFactory.make(
                    "queue", f"queue-pre-selector-slot{slot_idx}-apphost{apphost_idx}"
                )
                if not queue_pre:
                    logger.error(
                        f"Failed to create pre-selector queue for slot {slot_idx}, apphost {apphost_idx}"
                    )
                    return False

                queue_pre.set_property("max-size-buffers", 10)
                queue_pre.set_property("max-size-bytes", 0)
                queue_pre.set_property("max-size-time", 0)

                # Add to pipeline
                self.pipeline.add(filesrc)
                self.pipeline.add(videoparse)
                self.pipeline.add(queue_pre)

                # Link: filesrc -> videoparse -> queue -> selector
                if not filesrc.link(videoparse):
                    logger.error(
                        f"Failed to link filesrc to videoparse for slot {slot_idx}, apphost {apphost_idx}"
                    )
                    return False

                if not videoparse.link(queue_pre):
                    logger.error(
                        f"Failed to link videoparse to queue for slot {slot_idx}, apphost {apphost_idx}"
                    )
                    return False

                if not queue_pre.link(selector):
                    logger.error(
                        f"Failed to link queue to selector for slot {slot_idx}, apphost {apphost_idx}"
                    )
                    return False

            # Set the active pad based on initial assignment
            assigned_apphost = self.input_assignments[slot_idx]
            sink_pads = list(selector.iterate_sink_pads())
            if assigned_apphost < len(sink_pads):
                selector.set_property("active-pad", sink_pads[assigned_apphost])
                logger.info(f"Set slot {slot_idx} to use apphost {assigned_apphost}")

        # Add bus watch for messages
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)

        logger.info("Pipeline built successfully")
        return True

    def on_bus_message(self, bus, message):
        """Handle GStreamer bus messages."""
        t = message.type

        if t == Gst.MessageType.EOS:
            logger.info("End-of-stream received")
            self.stop()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Pipeline error: {err.message}")
            logger.error(f"Debug info: {debug}")
            self.stop()
        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Pipeline warning: {warn.message}")
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(
                    f"Pipeline state changed from {old_state.value_nick} to {new_state.value_nick}"
                )

    def start(self):
        """Start the pipeline."""
        if not self.pipeline:
            logger.error("Pipeline not built, call build_pipeline() first")
            return False

        logger.info("Starting pipeline...")
        ret = self.pipeline.set_state(Gst.State.PLAYING)

        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Failed to set pipeline to PLAYING state")
            return False

        logger.info("Pipeline started successfully")
        logger.info(f"TCP server listening on port 6000")
        logger.info(
            f"Tiling {self.num_inputs} slots in {self.grid_cols}x{self.grid_rows} grid from {self.num_apphosts} apphosts"
        )

        return True

    def run(self):
        """Run the main loop."""
        self.loop = GLib.MainLoop()

        try:
            logger.info("Entering main loop...")
            self.loop.run()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()

    def stop(self):
        """Stop the pipeline and quit the main loop."""
        logger.info("Stopping pipeline...")

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        if self.loop:
            self.loop.quit()

        logger.info("Pipeline stopped")


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get configuration from environment variables
    num_inputs = int(os.environ.get("NUM_INPUTS", "16"))  # N - number of tile slots
    num_apphosts = int(
        os.environ.get("NUM_APPHOSTS", "4")
    )  # M - number of video sources
    grid_cols = int(os.environ.get("GRID_COLS", "4"))
    grid_rows = int(os.environ.get("GRID_ROWS", "4"))

    logger.info(f"Starting Static Tiler Service")
    logger.info(
        f"Configuration: {num_inputs} inputs, {num_apphosts} apphosts, {grid_cols}x{grid_rows} grid"
    )

    # Create tiler
    tiler = StaticTiler(
        num_inputs=num_inputs,
        num_apphosts=num_apphosts,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
    )

    # Build pipeline
    if not tiler.build_pipeline():
        logger.error("Failed to build pipeline")
        sys.exit(1)

    # Start pipeline
    if not tiler.start():
        logger.error("Failed to start pipeline")
        sys.exit(1)

    # Handle signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        tiler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run main loop
    tiler.run()


if __name__ == "__main__":
    main()
