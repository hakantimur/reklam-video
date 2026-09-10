// Remotion CLI config. Spec: docs/IMPLEMENTATION_SPEC_TR.md sec.16.2 -- Node
// renderer only ever consumes validated Timeline JSON + allow-listed asset
// references, it never executes LLM-generated JavaScript.
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// The ffmpeg fetched by scripts/setup/fetch_binaries.py into
// backend/.tools/ffmpeg/bin is used when the FFMPEG_BINARY / PATH does not
// already point at one (see docs/DECISIONS.md, "ffmpeg / scrcpy binary
// temini"). Remotion 4's Rust compositor does most of the frame work
// itself, but audio muxing and some environments still shell out to a
// system ffmpeg, so we point at it explicitly when present.
import { existsSync } from "node:fs";
import path from "node:path";

// remotion.config.ts is bundled and executed as CommonJS by the Remotion
// CLI's own config loader (even though this repo is otherwise ESM), so
// __dirname is available here and import.meta.url is not.
const localFfmpegDir = path.resolve(__dirname, "../../backend/.tools/ffmpeg/bin");
if (existsSync(path.join(localFfmpegDir, "ffmpeg.exe"))) {
  Config.setFfmpegExecutable(path.join(localFfmpegDir, "ffmpeg.exe"));
  Config.setFfprobeExecutable(path.join(localFfmpegDir, "ffprobe.exe"));
}
