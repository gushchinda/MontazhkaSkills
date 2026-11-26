"""Extract native-resolution source frames for a reference shot and record their timestamps."""
import argparse
import csv
from pathlib import Path
import re
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", type=float, default=0.0, help="inclusive, in seconds")
    parser.add_argument("--end", type=float, help="exclusive, in seconds")
    parser.add_argument("--fps", type=float, default=4.0, help="target sampling rate")
    args = parser.parse_args()
    if args.fps <= 0 or args.start < 0 or (args.end is not None and args.end <= args.start):
        parser.error("invalid sampling rate or time range")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("choose an empty output directory for this shot")
    args.output.mkdir(parents=True, exist_ok=True)
    # Select the first source frame in each time bin. Keep PTS for VFR inputs.
    bucket = f"floor((t-{args.start})*{args.fps}+0.000001)"
    prev = f"floor((prev_selected_t-{args.start})*{args.fps}+0.000001)"
    select = f"gte(t,{args.start})"
    if args.end is not None:
        select += f"*lt(t,{args.end})"
    select += f"*(isnan(prev_selected_t)+gt({bucket},{prev}))"
    result = subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(args.video),
                             "-map","0:v:0","-vf",f"select='{select}',showinfo",
                             "-fps_mode","vfr","-start_number","1",
                             str(args.output/"frame_%05d.png")],stderr=subprocess.PIPE,text=True)
    if result.returncode:
        sys.exit(result.stderr[-2500:])
    times = re.findall(r"showinfo[^\n]*?\bn:\s*\d+\s+pts:\s*-?\d+\s+pts_time:(\S+)",result.stderr)
    files = sorted(args.output.glob("frame_*.png"))
    if not files or len(times) != len(files):
        sys.exit("No usable frame/timestamp match; check the source and interval")
    with (args.output/"timings.csv").open("w",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["source_seconds","file"])
        writer.writerows((t,p.name) for t,p in zip(times,files))
    print(f"{len(files)} source frames in {args.output}")

if __name__ == "__main__":
    main()
