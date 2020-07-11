import subprocess
import wave
from pathlib import Path
import shlex

def convert(filepath: Path, to_wav: bool) -> Path:
    """Attempts to convert a file from .mp3 to .wav or vice versa"""
    outfile = filepath.with_suffix(".wav") if to_wav else filepath.with_suffix(".mp3")
    inf = filepath.absolute()
    outf = outfile.absolute()
    if to_wav:
        cmd = f'ffmpeg -y -i "{inf}" -acodec pcm_u8 -ar 44100 "{outf}"'
    else:
        cmd = f'ffmpeg -y -i "{inf}" -acodec libmp3lame -ab 128k "{outf}"'
    subprocess.Popen(shlex.split(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
    return outfile


def join_wavs(file_1: Path, file_2: Path) -> Path:
    for p in [file_1, file_2]:
        if not p.exists():
            # NOTE: Should this error be tailored towards users of the bot or the developer?
            raise FileNotFoundError(f"'{p.stem}' does not exist!")

    # Get wave file data
    wav_data = []
    for f in [file_1, file_2]:
        with wave.open(str(f), "rb") as w:
            wav_data.append([w.getparams(), w.readframes(w.getnframes())])

    fname = Path(f"{file_1.parent}/{file_1.stem}_{file_2.stem}.wav")
    if fname.exists():
        raise FileExistsError(f"{fname.stem} already exists!")

    # Join wave files
    with wave.open(str(fname), "wb") as wavfile:
        wavfile.setparams(wav_data[0][0])
        wavfile.writeframes(wav_data[0][1])
        wavfile.writeframes(wav_data[1][1])

    # Return filename and relative filepath
    return fname
