import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


def inspect(path, decode, timeout):
    if path.stat().st_size == 0:
        return 'suspect', 'Empty file'
    if path.name.endswith(('.part', '.ytdl', '.tmp')):
        return 'suspect', 'Incomplete download artifact'
    try:
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_streams', '-show_format',
             '-of', 'json', str(path)],
            capture_output=True, text=True, timeout=timeout,
        )
        if probe.returncode or probe.stderr.strip():
            return 'suspect', probe.stderr.strip() or 'ffprobe failed'
        data = json.loads(probe.stdout)
        streams = data.get('streams', [])
        video = any(s.get('codec_type') == 'video' and
                    not s.get('disposition', {}).get('attached_pic') for s in streams)
        audio = any(s.get('codec_type') == 'audio' for s in streams)
        if not video or not audio:
            missing = ', '.join(name for name, present in [('video', video), ('audio', audio)]
                                if not present)
            return 'suspect', f'Missing {missing} stream'
        if decode:
            result = subprocess.run(
                ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-threads', '1',
                 '-i', str(path), '-map', '0:v:0', '-map', '0:a:0',
                 '-threads', '1', '-f', 'null', '-'],
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode or result.stderr.strip():
                return 'suspect', result.stderr.strip() or 'Decode failed'
        return 'ok', 'Decode passed' if decode else 'Headers and streams passed'
    except subprocess.TimeoutExpired:
        return 'unchecked', f'Exceeded {timeout} seconds; retry with a higher --timeout'
    except (OSError, ValueError) as error:
        return 'unchecked', str(error)


def main():
    parser = argparse.ArgumentParser(description='Read-only trailer integrity scan.')
    parser.add_argument('root', type=Path)
    parser.add_argument('--dirs', nargs='+', default=['trailers'],
                        help='Trailer directory names (default: trailers)')
    parser.add_argument('--decode', action='store_true', help='Decode audio/video to check integrity')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout per subprocess in seconds')
    parser.add_argument('--report', type=Path, default=Path('trailer-scan.jsonl'))
    args = parser.parse_args()
    args.root = args.root.resolve()
    if not args.root.is_dir():
        parser.error('root must be an existing directory')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    for command in ['ffprobe'] + (['ffmpeg'] if args.decode else []):
        if not shutil.which(command):
            parser.error(f'{command} is not on PATH')

    previous = {}
    if args.report.exists():
        with args.report.open() as report:
            for line in report:
                try:
                    record = json.loads(line)
                    previous[record['path']] = record
                except (ValueError, KeyError):
                    continue
    counts = {'ok': 0, 'suspect': 0, 'unchecked': 0}
    extensions = {'.webm', '.mp4', '.mkv', '.mov', '.avi', '.m4v', '.ts', '.part', '.ytdl', '.tmp'}

    def walk_error(error):
        counts['unchecked'] += 1
        print(f'UNCHECKED DIRECTORY: {error}', flush=True)

    with args.report.open('a') as report:
        report.write('\n')
        for directory, _, filenames in os.walk(args.root, onerror=walk_error):
            folder = Path(directory)
            if not set(folder.relative_to(args.root).parts).intersection(args.dirs) and folder.name not in args.dirs:
                continue
            for filename in sorted(filenames):
                path = folder / filename
                if path.suffix.lower() not in extensions:
                    continue
                try:
                    stat = path.stat()
                    signature = [stat.st_size, stat.st_mtime_ns, args.decode, args.timeout]
                    cached = previous.get(str(path), {})
                    if cached.get('signature') == signature and cached.get('status') in ('ok', 'suspect'):
                        record = cached
                    else:
                        status, reason = inspect(path, args.decode, args.timeout)
                        record = dict(path=str(path), signature=signature, status=status, reason=reason)
                        report.write(json.dumps(record) + '\n')
                        report.flush()
                    counts[record['status']] += 1
                    if record['status'] != 'ok':
                        print(f"{record['status'].upper()}: {json.dumps(str(path))}\n  {record['reason']}", flush=True)
                    elif counts['ok'] % 25 == 0:
                        print(f"Checked {sum(counts.values())} files...", flush=True)
                except OSError as error:
                    counts['unchecked'] += 1
                    print(f'UNCHECKED: {json.dumps(str(path))}: {error}', flush=True)
    print(f"Finished: {counts['ok']} passed, {counts['suspect']} suspect, {counts['unchecked']} unchecked.")
    print(f'Report: {args.report.resolve()}')
    print('Suspect files require review. A clean scan cannot detect every shortened but valid encode.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nInterrupted. Rerun the same command to resume from saved results.')
        raise SystemExit(130)
