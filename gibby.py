#!/usr/bin/env python3
import os,subprocess,datetime,argparse,sys,shutil,json,struct

YOUTUBE_DL_PROCESS="youtube-dl"
FFMPEG_PROCESS="ffmpeg"

DEBUG=False

#swapping subprocess to shutil, subprocess doesn't throw error as assumed. Still returns status 1 but with default system response for missing command
def command_exists(comm):return True if shutil.which(comm) else False

def parse_duration(length):
    spl=length.split(":")
    s=m=h=0
    if len(spl)>0:s=int(spl[-1])
    if len(spl)>1:m=int(spl[-2])
    if len(spl)>2:h=int(spl[-3])
    return datetime.timedelta(hours=h,minutes=m,seconds=s)

def _try_parse(json_str):
    try:return True,json.loads(json_str)
    except:return False,None

def rand():return struct.unpack("!Q",os.urandom(8))

#basiclly pointless lmao
def _json_get(key_path,data,default=None):
    if isinstance(key_path,str):key_path=key_path.split("/")
    if len(key_path)==0:return default
    elif len(key_path)==1:return data[key_path[0]] if key_path[0] in data else default
    else:
        if key_path[0] in data:
            val=data[key_path[0]]
            for i in range(1,len(key_path)):
                if key_path[i] in val:val=val[key_path[i]]
                else:return default
            return val

# JSON INFORMATION GRABBERS
def _playlist_title(data):return _json_get("playlist_title",data)
def _playlist_index(data):return _json_get("playlist_index",data)
def _get_playlist_id(data):return _json_get("playlist_id",data)
def _get_formats(data):return _json_get("requested_formats",data)
def _get_webpage_url(data):return _json_get("webpage_url",data)
#return video, audio codecs
def _get_codecs(data):return [_json_get("vcodec",data),_json_get("acodec",data)]
def _get_playlist_size(data):return _json_get("n_entries",data)
def _get_video_title(data):return _json_get("fulltitle",data)
def _get_video_duration(data):return _json_get("duration",data)
def _get_video_filename(data):return _json_get("_filename",data)

#-j goes through entire playlist, printing per video
#can do --no-playlist for downloading first information
def get_video_information(ytdl_url):
    status,output=subprocess.getstatusoutput(_command_ytdl_info(ytdl_url))
    is_parsed,parsed_data=_try_parse(output)
    if is_parsed:return parsed_data

def execute_print(cmd):
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,universal_newlines=True)
    for stdout_line in iter(p.stdout.readline,""):
        print(stdout_line,end="")
    p.stdout.close()
    status=p.wait()
    return status

#open connection to ytdl process, and yield any JSON information that comes out
def yield_subprocess(command):
    p=subprocess.Popen(command,stdout=subprocess.PIPE,universal_newlines=True)
    for line in iter(p.stdout.readline,""):
        is_parsed,parsed=_try_parse(line)
        if is_parsed:yield parsed
    p.stdout.close()
    status=p.wait()
    return status

def tformat(size=3):return ":".join(["{:02}"]*3)

def strfdelta(deltatime,full_time=False):
    total_seconds=deltatime.total_seconds()
    hours,rem=divmod(total_seconds,3600)
    mins,sec=divmod(rem,60)
    if hours>0 or full_time:return tformat().format(int(hours),int(mins),int(sec))
    elif mins>0:return tformat(2).format(int(mins),int(sec))
    else:return "{:02}".format(int(sec))

def create_youtubedl_download(video_url,output_location=None):return "%s \"%s\"%s"%(YOUTUBE_DL_PROCESS,video_url," -o \"%s\""%output_location if output_location else "")
def _command_ytdl_download(video_src,output_location=None):return "{0} \"{1}\"{2}".format(YOUTUBE_DL_PROCESS,video_src,(" -o \"%s\""%output_location) if output_location else "")
#had to add -strict -2 to allow opus in MP4 video, will have to look at tweaking FFMPEG command in future
def _command_ytdl_info(video_src): #with max-downloads the process should end after 1 video JSON grab
    return "{0} \"{1}\" -j {2} 1".format(YOUTUBE_DL_PROCESS,video_src,ytdl_max_downloads)

def create_ffmpeg_command(video_src,audio_src,start_time,output_filename):
    return "{0} -y -ss {1} -i \"{2}\" -ss {1} -i \"{3}\" -map 0:v -c:v copy -map 1:a -c:a copy -t 7:10  -strict -2 \"{4}\"".format(
        FFMPEG_PROCESS, #0
        strfdelta(start_time,True), #1
        video_src, #2
        audio_src, #3
        output_filename #4
    )

#convert argparse variable into the parsed name
#TODO actually look into how argparse creates Namespace key names
def argparse_name(n):
    n=n.replace("--","")
    if n[0]=="-":return n[1:].replace("-","_")
    else:return n.replace("-","_")

def format_extra_args(args):
    a=[]
    for k,v in args.items():
        if v:a.append("%s %s"%(k,v))
        else:a.append(k)
    return " ".join(a)

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

#YTDL COMMANDS
ytdl_no_playlist="--no-playlist"
ytdl_plist_start="--playlist-start"
ytdl_plist_end="--playlist-end"
ytdl_max_downloads="--max-downloads"
ytdl_output_format1="-o"
ytdl_output_format2="--output-template"
ytdl_passto=[ytdl_no_playlist,ytdl_plist_start,ytdl_plist_end,ytdl_max_downloads]
aparser.add_argument(ytdl_no_playlist,action="store_true",help="Only download one video")
aparser.add_argument(ytdl_plist_start,type=int,help="The playlist index to start downloading from")
aparser.add_argument(ytdl_plist_end,type=int,help="The index to stop downloading playlist")
aparser.add_argument(ytdl_max_downloads,type=int,help="")
aparser.add_argument(ytdl_output_format1,ytdl_output_format2,help="The output template for file names")

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

parsed_ytdl_strs={}
namespace_keys=[argparse_name(f) for f in ytdl_passto]
for k,v in parsed.__dict__.items():
    if not k in namespace_keys:continue
    if not v:continue
    k_orig=ytdl_passto[namespace_keys.index(k)]
    if type(v)==bool:parsed_ytdl_strs[k_orig]=None
    else:parsed_ytdl_strs[k_orig]="\"%s\""%v if type(v)==str else v

successful=0
for video in vid:
    try:
        def fail_parse(msg,debug=True):
            print("Failed to parse JSON \"%s\""%msg)
            if debug:
                filename=os.path.expanduser("~/Documents/DEBUG_json_%s.json"%rand())
                with open(filename,'w')as out:
                    out.write(json.dumps(vidinfo,indent="\t"))
            raise ValueError
        print("Grabbing video info for %s"%video)
        vidinfo=get_video_information(video)
        if vidinfo:
            plist_title=_playlist_title(vidinfo)
            plist_index=_playlist_index(vidinfo)
            plist_size=_get_playlist_size(vidinfo)
            plist_id=_get_playlist_id(vidinfo)
            video_url=_get_webpage_url(vidinfo)
            ytdl_url=video_url
            vduration=_get_video_duration(vidinfo)
            if vduration is None:fail_parse("Duration is None")
            is_playlist = plist_title or plist_index or plist_id
            #now that's a big brain move right there
            download_playlist=not parsed.no_playlist
            total_count=1
            #create final ytdl
            if is_playlist:
                ytdl_url+="&list=%s"%plist_id
                if not ytdl_plist_start in parsed_ytdl_strs:
                    parsed_ytdl_strs[ytdl_plist_start]=plist_index
                #index starts at 1
                total_count=plist_size-(parsed_ytdl_strs[ytdl_plist_start]-1)
            ytdl_command="{0} \"{1}\" -j".format(YOUTUBE_DL_PROCESS,ytdl_url)
            if len(parsed_ytdl_strs)>0:ytdl_command+=" %s"%format_extra_args(parsed_ytdl_strs)
            if total_count>1:
                print("Downloading %s videos from playlist %s"%(total_count,plist_title))
            for js in yield_subprocess(ytdl_command):
                try:
                    f_name=_get_video_filename(js) #local filename
                    f_title=_get_video_title(js) #youtube name
                    f_duration=_get_video_duration(js)
                    f_streams=_get_formats(js)
                    f_url=_get_webpage_url(js)
                    if not f_streams:fail_parse("Stream data")
                    if len(f_streams)<2:fail_parse("Stream data less than 2")
                    vstream=f_streams[0]
                    astream=f_streams[1]
                    v_url=vstream["url"]
                    v_codec=vstream["vcodec"]
                    a_url=astream["url"]
                    a_codec=astream["acodec"]
                    if a_codec == "opus":a_codec="libopus"
                    duration=datetime.timedelta(seconds=f_duration)
                    cut_longer=parsedtime.total_seconds()>duration.total_seconds()
                    stat=0
                    print("Downloading {0} -> {1}".format(f_title,f_name))
                    if cut_longer: #YTDL download
                        print("Downloading using YTDL as specified cut is longer than video")
                        ytdl_command="{0} \"{1}\" -o {2}"
                        stat=execute_print(ytdl_command)
                        if stat:
                            print("YTDL returned non-zero error code, assuming download failed")
                    else: #FFMPEG download
                        start_time=duration-parsedtime
                        print("Starting cut at %s"%strfdelta(start_time,True))
                        ffmpeg_command=create_ffmpeg_command(vstream["url"],astream["url"],start_time,f_name,v_codec,a_codec)
                        stat=execute_print(ffmpeg_command)
                        if stat:
                            print("ffmpeg returned non-zero error code, assuming download failed")
                    if os.path.isfile(f_name):
                        if stat:
                            print("File still exists at {0}, probably incomplete download".format(f_name))
                            continue
                        fsize=os.path.getsize(f_name)
                        print("Downloaded {1} bytes".format(f_title,fsize))
                    else:print("Can't find file at {0}, assuming failed".format(f_name))
                except ValueError as ve:raise ve
                except Exception as e:
                    print("[ERROR] unknown exception occured when downloading ")
                    print(e)
                    if DEBUG:raise e
        else:
            print("Failed to parse youtube-dl output")
    except ValueError as ve:pass
    except Exception as e:
        print("UNHANDLED EXCEPTION OCCURED%s"%(", SKIPPING" if len(vid)>1 else ""))
        print(e)
        if DEBUG:raise e
print("All tasks completed. %s reported successful"%successful)
