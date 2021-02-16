import xml.etree.ElementTree as ET
import datetime
import subprocess
import os
import sys

list_filenames_to_concatenate = []
input_path_project = -1
input_audio_filename = -1
# slidesXML_filename = "slides.xml"
rec_start_time = -1
rec_stop_time = -1


def clear_slides_file(slidesXML_filename):
    print("clear_slides_file: " + slidesXML_filename)
    with open(input_path_project + slidesXML_filename,
              '+w') as file:
        file.truncate(0)
        file.close()


def write_line_into_slides_file(slidesXML_filename, line_to_write):
    print("write_line_into_slides_file: ", input_path_project + slidesXML_filename + " " + line_to_write)
    with open(input_path_project + slidesXML_filename,
              'a') as file:
        file.write(line_to_write + '\n')
    file.close()


def calculate_cut_time_slides(slides_filename):
    file = open(input_path_project + slides_filename, 'r')
    lines = file.readlines()
    time_length = 0
    for line in lines:
        if line.find("duration") != -1:
            start_pos = len("duration") + 1
            end_pos = len(line)
            time_length = time_length + float(line[start_pos:end_pos])
    time_length_format_hours = int(time_length / 3600)
    time_length_format_minutes = int(time_length / 60)
    time_length_format_seconds = int(time_length % 60)
    return str(time_length_format_hours).zfill(2) + ":" + str(time_length_format_minutes).zfill(2) + ":" + str(time_length_format_seconds).zfill(2)


def create_audio_track(rec_start_time, rec_stop_time):
    print("ffmpeg -y -i " + input_path_project + "audio/" + input_audio_filename + " -ss " + rec_start_time + " -to " + rec_stop_time + " -c copy " + input_path_project + "output_audio_track.mkv")
    os.system("ffmpeg -y -i " + input_path_project + "audio/" + input_audio_filename + " -ss " + rec_start_time + " -to " + rec_stop_time + " -c copy " + input_path_project + "output_audio_track.mkv")


def create_slides_video_track(slides_filename):
    if os.stat(input_path_project + slides_filename).st_size != 0:
        print("ffmpeg -y -f concat -i " + input_path_project + slides_filename + " " + input_path_project + slides_filename + ".mp4")
        os.system("ffmpeg -y -f concat -i " + input_path_project + slides_filename + " " + input_path_project + slides_filename + ".mp4")
        cut_time = calculate_cut_time_slides(slides_filename)
        os.system("ffmpeg -y -i " + input_path_project + slides_filename + ".mp4 -ss 00:00:00 -t " + cut_time +" -async 1 " + input_path_project + slides_filename + "_temp.mp4")
        os.system("mv -f " + input_path_project + slides_filename + "_temp.mp4 " + input_path_project + slides_filename + ".mp4")


def create_video_tracks():
    print("list_filenames_to_concatenate", str(list_filenames_to_concatenate))

    for filename in list_filenames_to_concatenate:
        if "slides" in filename:
            create_slides_video_track(filename)

    slides_deskshare_input_str = ""
    for filename in list_filenames_to_concatenate:
        if "slides" in filename:
            slides_deskshare_input_str = slides_deskshare_input_str + " -i " + input_path_project + filename + ".mp4"
        else:
            slides_deskshare_input_str = slides_deskshare_input_str + " -i " + input_path_project + filename

    filter_complex_str = "-filter_complex \""
    filter_complex_str_left_side = ""
    filter_complex_str_right_side = ""
    for filename in list_filenames_to_concatenate:
        index = list_filenames_to_concatenate.index(filename)
        filter_complex_str_left_side = filter_complex_str_left_side + "[" + str(index) + ":v]scale=640x640,setdar=16/9[v" + str(index) + "];"
        filter_complex_str_right_side = filter_complex_str_right_side + "[v" + str(index) + "][" + str(len(list_filenames_to_concatenate)) + ":a]"

    filter_complex_str = filter_complex_str + filter_complex_str_left_side + " " + filter_complex_str_right_side + "concat=n=" + str(len(list_filenames_to_concatenate)) + ":v=1:a=1[v][a]\""
    ffmpeg_command_str = "ffmpeg -y" + slides_deskshare_input_str + " -f lavfi -t 0.1 -i anullsrc " + filter_complex_str + " -map [v] -map [a] " + input_path_project + "concat_output_file.mp4"
    print(ffmpeg_command_str)
    os.system(ffmpeg_command_str)


def cut_video_concat_file(record_audio_start_timestamp, record_audio_stop_timestamp, StartWebRTCDesktopShareEvent_timestamp, webRTC_stop_desktop_share_event_timestamp):
    if int(StartWebRTCDesktopShareEvent_timestamp) != -1 and int(StartWebRTCDesktopShareEvent_timestamp) < int(record_audio_start_timestamp):
        cut_diff_start = int(record_audio_start_timestamp) - int(StartWebRTCDesktopShareEvent_timestamp)
        cut_video_start_time = calc_rec_start_stop_time(record_audio_start_timestamp, StartWebRTCDesktopShareEvent_timestamp)

        video_duration = os.popen("ffprobe -i " + input_path_project + "concat_output_file.mp4 -show_format -v quiet | grep duration").read()
        video_duration_start_pos = video_duration.rindex('duration') + len('duration') + 1
        video_duration_end_pos = video_duration.rindex('.')
        video_duration = video_duration[video_duration_start_pos:video_duration_end_pos]

        diff_video_cut_time = datetime.datetime.fromtimestamp(int(video_duration)-(int(webRTC_stop_desktop_share_event_timestamp) - int(record_audio_stop_timestamp)) / 1000.0)
        diff_video_cut_time = diff_video_cut_time.replace(hour=diff_video_cut_time.hour - 1)

        cut_video_stop_time = str(diff_video_cut_time.hour) + ":" + str(diff_video_cut_time.minute) + ":" + str(diff_video_cut_time.second)

        print("ffmpeg -y -i " + input_path_project + "concat_output_file.mp4" + " -ss " + cut_video_start_time + " -to " + cut_video_stop_time + " -c copy " + input_path_project + "concat_output_file_final.mp4")
        os.system("ffmpeg -y -i " + input_path_project + "concat_output_file.mp4" + " -ss " + cut_video_start_time + " -to " + cut_video_stop_time + " -c copy " + input_path_project + "concat_output_file_final.mp4")
    else:
        os.system("mv -f " + input_path_project + "concat_output_file.mp4 " + input_path_project + "concat_output_file_final.mp4")


def create_final_video_audio_track():
    ffmpeg_final_command_str = "ffmpeg -y -i " + input_path_project + "concat_output_file_final.mp4 -f lavfi -t 0.1 -i anullsrc -i " + input_path_project + "output_audio_track.mkv -filter_complex \"[0:v]scale=640x640,setdar=16/9[v0]; [v0][2:a]concat=n=1:v=1:a=1[v][a]\" -map [v] -map [a] " + input_path_project + "final_output.mp4"
    print(ffmpeg_final_command_str)
    os.system(ffmpeg_final_command_str)


def calc_rec_start_stop_time(record_audio_timestamp, record_start_recording_event_timestamp):
    record_audio_datetime = datetime.datetime.fromtimestamp((int(record_audio_timestamp) - int(record_start_recording_event_timestamp)) / 1000.0)
    record_audio_datetime = record_audio_datetime.replace(hour=record_audio_datetime.hour-1)
    return str(record_audio_datetime.hour) + ":" + str(record_audio_datetime.minute) + ":" + str(record_audio_datetime.second)


def start_end_times(record_start_recording_event_timestamp, record_audio_start_timestamp, record_audio_stop_timestamp):
    global rec_start_time
    rec_start_time = calc_rec_start_stop_time(record_audio_start_timestamp, record_start_recording_event_timestamp)

    global rec_stop_time
    rec_stop_time = calc_rec_start_stop_time(record_audio_stop_timestamp, record_start_recording_event_timestamp)


def extract_XML():
    tree = ET.parse(input_path_project + 'events.xml')
    root = tree.getroot()
    recent_timestamp = -1
    record_audio_start_timestamp = -1
    record_audio_stop_timestamp = -1
    record_start_recording_event_timestamp = -1
    StartWebRTCDesktopShareEvent_timestamp = -1
    webRTC_start_desktop_share_event_timestamp = -1
    webRTC_stop_desktop_share_event_timestamp = -1
    record_status = False
    last_used_slide_filename = -1
    slidesXML_counter = 1
    slide_subpath = -1

    clear_slides_file("slidesXML" + str(slidesXML_counter))

    for event in root.findall('event'):
        for t in event.iter():
            matches = [recordEvent for recordEvent in t.attrib.values() if recordEvent == 'StartRecordingEvent']
            if matches:
                if record_start_recording_event_timestamp == -1:
                    record_start_recording_event_timestamp = event.find('timestampUTC').text
                    filename = event.find('filename').text
                    filename_start_pos = filename.rindex('meetings') + len('meetings') + 1
                    filename_end_pos = len(filename) # .index("</filename>") - 1
                    global input_audio_filename
                    input_audio_filename = filename[filename_start_pos:filename_end_pos]

            matches = [recordEvent for recordEvent in t.attrib.values() if recordEvent == 'RecordStatusEvent']
            if matches:
                record_status_local = event.find('status').text
                if not record_status and record_status_local == "true":
                    record_status = True
                    record_audio_start_timestamp = event.find('timestampUTC').text

                if record_status and record_status_local == "false":
                    record_status = False
                    record_audio_stop_timestamp = event.find('timestampUTC').text
                    current_timestamp = record_audio_stop_timestamp
                    duration_timestamp = (int(current_timestamp) - int(recent_timestamp)) / 1000
                    if slide_subpath != -1:
                        write_line_into_slides_file("slidesXML" + str(slidesXML_counter), 'duration ' + str(duration_timestamp))
                        write_line_into_slides_file("slidesXML" + str(slidesXML_counter), 'file \'' + slide_subpath + slide_filename + '\'')


            matches = [recordEvent for recordEvent in t.attrib.values() if recordEvent == 'StartWebRTCDesktopShareEvent'] # and record_status]
            if matches:
                # TODO: file name check for correctly recorded .webm file is still missing
                current_timestamp = event.find('timestampUTC').text
                if not record_status:
                    StartWebRTCDesktopShareEvent_timestamp = event.find('timestampUTC').text
                else:
                    duration_timestamp = (int(current_timestamp) - int(recent_timestamp)) / 1000
                    if slide_subpath != -1:
                        write_line_into_slides_file("slidesXML" + str(slidesXML_counter), 'duration ' + str(duration_timestamp))
                        write_line_into_slides_file("slidesXML" + str(slidesXML_counter), 'file \'' + slide_subpath + slide_filename + '\'')

                    meeting_id = event.find('meeting_id').text
                    filename = event.find('filename').text
                    filename_start_pos = filename.rindex(meeting_id) + len(meeting_id) + 1
                    filename_end_pos = len(filename) # .index("</filename>") - 1
                    filename = filename[filename_start_pos:filename_end_pos]
                    list_filenames_to_concatenate.append("deskshare/" + filename)

            matches = [recordEvent for recordEvent in t.attrib.values() if recordEvent == 'StopWebRTCDesktopShareEvent'] # and record_status]
            if matches:
                current_timestamp = event.find('timestampUTC').text

                if not record_status:
                    webRTC_stop_desktop_share_event_timestamp = event.find('timestampUTC').text
                else:
                    slidesXML_counter = slidesXML_counter + 1
                    clear_slides_file("slidesXML" + str(slidesXML_counter))
                    write_line_into_slides_file("slidesXML" + str(slidesXML_counter), 'file \'' + slide_subpath + last_used_slide_filename + '\'')
                    list_filenames_to_concatenate.append("slidesXML" + str(slidesXML_counter))
                    recent_timestamp = current_timestamp

            matches = [recordEvent for recordEvent in t.attrib.values() if recordEvent == 'GotoSlideEvent' and record_status]
            slide_filename = last_used_slide_filename
            if matches:
                id = event.find('id').text
                id_start_pos = 0
                id_end_pos = id.index("/")
                id = id[id_start_pos:id_end_pos]
                slide_subpath = "presentation/" + str(id) + "/svgs/"

            if matches and recent_timestamp == -1:
                recent_timestamp = record_audio_start_timestamp
                slide_filename = 'slide1.svg'
                write_line_into_slides_file("slidesXML" + str(slidesXML_counter), 'file \'' + slide_subpath + slide_filename + '\'')
                list_filenames_to_concatenate.append("slidesXML" + str(slidesXML_counter))

            if matches:
                slide_filename = 'slide' + str(int(event.find('slide').text) + 1) + '.svg'
                current_timestamp = event.find('timestampUTC').text
                duration_timestamp = (int(current_timestamp) - int(recent_timestamp)) / 1000
                write_line_into_slides_file("slidesXML" + str(slidesXML_counter), 'duration ' + str(duration_timestamp))
                write_line_into_slides_file("slidesXML" + str(slidesXML_counter), 'file \'' + slide_subpath + slide_filename + '\'')
                recent_timestamp = current_timestamp

            last_used_slide_filename = slide_filename

    start_end_times(record_start_recording_event_timestamp, record_audio_start_timestamp, record_audio_stop_timestamp)
    create_audio_track(rec_start_time, rec_stop_time)
    create_video_tracks()
    cut_video_concat_file(record_audio_start_timestamp, record_audio_stop_timestamp, StartWebRTCDesktopShareEvent_timestamp, webRTC_stop_desktop_share_event_timestamp)
    create_final_video_audio_track()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        input_path_project = sys.argv[1] + "/"
        print(input_path_project)
        extract_XML()
    else:
        print("Error. No path specified.")
        exit(1)
