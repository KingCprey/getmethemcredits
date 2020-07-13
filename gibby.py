import os,subprocess,datetime,argparse,sys

YOUTUBE_DL_PROCESS="youtube-dl"
FFMPEG_PROCESS="ffmpeg"

#just a quick run of the program
def command_exists(comm):
    try:
        subprocess.getstatusoutput("%s")
        return True
    except:return False

def parse_duration(length):
    spl=length.split(":")
    s=m=h=0
    if len(spl)>0:s=int(spl[-1])
    if len(spl)>1:m=int(spl[-2])
    if len(spl)>2:h=int(spl[-3])
    return datetime.timedelta(hours=h,minutes=m,seconds=s)

def get_video_information(video_url):
    """
    1. video stream
    2. audio stream
    3. output filename (title-id.ext)
    4. video duration
    """
    status,output=subprocess.getstatusoutput("%s -g --get-duration --get-filename \"%s\""%(YOUTUBE_DL_PROCESS,video_url))
    if status==0:
        lines=output.splitlines()
        if len(lines)>=4:
            video_stream=lines[0]
            audio_stream=lines[1]
            filename=lines[2]
            video_length=parse_duration(lines[3])
            return (video_stream,audio_stream,filename,video_length)

def strfdelta(deltatime):
    total_seconds=deltatime.total_seconds()
    hours,rem=divmod(total_seconds,3600)
    mins,sec=divmod(rem,60)
    return "{:02}:{:02}:{:02}".format(int(hours),int(mins),int(sec))

def create_youtubedl_download(video_url,output_location=None):return "%s \"%s\"%s"%(YOUTUBE_DL_PROCESS,video_url," -o \"%s\""%output_location if output_location else "")
def create_ffmpeg_command(video_src,audio_src,start_time,output_filename):
    return "%s -y -ss %s -i \"%s\" -ss %s -i \"%s\" -map 0:v -map 1:a -t 7:10 -acodec copy -vcodec copy \"%s\""%(FFMPEG_PROCESS,start_time,video_src,start_time,audio_src,output_filename)

if not command_exists(YOUTUBE_DL_PROCESS):
    print("Youtube-dl process (\"%s\") not found, exiting"%YOUTUBE_DL_PROCESS)
    sys.exit(1)
if not command_exists(FFMPEG_PROCESS):
    print("FFmpeg not found (\"%s\") not found, exiting"%FFMPEG_PROCESS)
    sys.exit(1)

#TODO HANDLE FILE OVERWRITE PROMPTS

aparser=argparse.ArgumentParser()
aparser.add_argument("video_url",help="A video url or text file with videos to download")
aparser.add_argument("start_time",help="How far before the end of the video to start the cut from (HH:MM:SS)")
#aparser.add_argument("-o","--output-file",help="Output location for file")
#aparser.add_argument("-d","--output-directory",help="The output directory to store files in")
parsed=aparser.parse_args()
parsedtime=None
try:parsedtime=parse_duration(parsed.start_time)
except:
    print("Failed to parse \"%s\" as a valid start time, please enter in format HH:MM:SS")
    sys.exit(1)
vid=parsed.video_url
if os.path.isfile(vid):
    with open(vid,'r')as inp:
        vid=inp.read().splitlines()
else:vid=[vid]
if len(vid)==0:
    print("No video URLs given, quitting")
    sys.exit(1)

for video in vid:
    try:
        print("Grabbing video info for %s"%video)
        vidinfo=get_video_information(video)
        if vidinfo:
            vstream=vidinfo[0]
            astream=vidinfo[1]
            filep=vidinfo[2]
            #ffmpeg seems to struggle with outputting to webm file, so if that occurs then will output to mkv
            #Not exactly literate in ffmpeg meself
            f,ext=os.path.splitext(filep)
            dur=vidinfo[3]
            print("Output filename: %s"%filep)
            print("Video duration: %s"%strfdelta(dur))
            cut_longer=parsedtime.total_seconds()>dur.total_seconds()
            if cut_longer:
                print("Amount to cut by is longer than video duration, will just download entire video")
                ytdl_command=create_youtubedl_download(video)
                st,outp=subprocess.getstatusoutput(ytdl_command)
                if not st==0:
                    print("Youtube-dl threw error, displaying output")
                    print(outp)
                else:
                    print("Download complete, file stored at %s"%filep)
            else:
                start_time=dur-parsedtime
                print("Starting cut at %s"%strfdelta(start_time))
                ffmpeg_command=create_ffmpeg_command(vstream,astream,strfdelta(start_time),filep)
                #print(ffmpeg_command)
                print("Starting ffmpeg, this may take some time")
                st,outp=subprocess.getstatusoutput(ffmpeg_command)
                if st==0:
                    print("Download complete, file stored at %s"%filep)
                else:
                    print("ffmpeg threw error, displaying output")
                    print(outp)
        else:
            print("Failed to parse youtube-dl output")
    except Exception as e:
        print("UNHANDLED EXCEPTION OCCURED%s"%(", SKIPPING" if len(vid)>1 else ""))
        print(e)
