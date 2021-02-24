import pandas as pd
from pydub import AudioSegment
import shutil
import argparse
import sys
import pydub
import ffmpeg
import os
import os.path
import time
from os import path
from collections import defaultdict


EMPTY_STRING = ""

def get_sec(time_str):
    """Get Seconds from time."""
    timeArray = time_str.split(':')
    if len(timeArray) == 2:
        m, s = time_str.split(':')
        return int(m) * 60 + int(s)
    elif len(timeArray) == 3:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + int(s)

def updateValue(newDfValue, currentValue):
    if newDfValue != EMPTY_STRING:
        return newDfValue
    else:
        return currentValue

def massageLongText(text):
    if text == EMPTY_STRING:
        return EMPTY_STRING
    else:
        if " " not in text:
            # we have processed this text before
            return text
        else:
            textSplit = text.split(" ")
            returnArray = []
            for text in textSplit:
                returnArray.append(text.capitalize())
            return "".join(returnArray)

def exportPodcastClips(csvDataframe, song, episodeName, exportedClipsFolderName) :
    story_Teller_Context = ""
    story_Description_Context = ""
    order_Context = ""
    previousEndTime = ""
    session_Num_Context = ""
    orderInOrderDictionary = defaultdict(int)
    for index, row in csvDataframe.iterrows():
        session_Num_Context = str(int(updateValue(row["session_num"], session_Num_Context)))
        order_Context = str(int(updateValue(row["order"], order_Context)))
        story_Teller_Context = updateValue(row["story_teller"].capitalize(), story_Teller_Context)
        story_Description_Context = updateValue(row["story_description"], story_Description_Context)
        story_Description_Context = massageLongText(story_Description_Context)
        order_Context = str(int(updateValue(row["order"], order_Context)))
        time_range = row["time_range"]
        timeRangeSplit = time_range.split("-")
        if (len(timeRangeSplit)) == 1:
            # only single time number exists, create tuple with previous end as the start of this section
            startTime = previousEndTime
            endTime = timeRangeSplit[0]
            previousEndTime = endTime
        else:
            # both numbers exist, extract now
            startTime = timeRangeSplit[0]
            endTime = timeRangeSplit[1]
            previousEndTime = endTime
        comment = row["comment"]
        comment = massageLongText(comment)

        clipName = episodeName + "_session " + session_Num_Context +  "_order" + order_Context + "_" + story_Teller_Context + "_" + str(orderInOrderDictionary[story_Teller_Context]).zfill(5) + "_" + startTime + "-" + endTime + "_" + story_Description_Context  + "_" + comment

        print("clip chunk identified: " + clipName)
        orderInOrderDictionary[story_Teller_Context] += 1

        if song is not None:
            startTimeSeconds = get_sec(startTime)
            startTimeMilliseconds = startTimeSeconds * 1000
            endTimeSeconds = get_sec(endTime)
            endTimeMilliseconds = endTimeSeconds * 1000

            audioFileLength = time.strftime('%H:%M:%S', time.gmtime(song.duration_seconds))
            if startTimeSeconds > song.duration_seconds:
                print("specified time " + str(startTime) + " for clip " + clipName + " is beyond the max length of the audio file " + audioFileLength)
                print("make sure you are referencing the right audio file")
                exit(0)
            if endTimeSeconds > song.duration_seconds:
                print("specified time " + str(endTime) + " for clip " + clipName + " is beyond the max length of the audio file " + audioFileLength)
                print("make sure you are referencing the right audio file")
                exit(0)

            songClip = song[startTimeMilliseconds:endTimeMilliseconds]
            clipName = clipName.replace("/", "-")
            clipNameWav = clipName + ".wav"
            print("attempting to export clip: " + clipNameWav + " into folder " + exportedClipsFolderName)
            songClip.export(os.path.join(exportedClipsFolderName, clipNameWav), format="wav")
            print("successfully exported clip: " + clipNameWav + "!!\n")

def exportMusicClips(csvDataframe, song, audioFileNameWithoutExtension, exportedClipsFolderName) :
    sessionTitle = ""
    previousEndTime = ""
    SESSION_TITLE_KEY = "session_title"
    try:
        sessionTitle = csvDataframe.iloc[0][SESSION_TITLE_KEY]
    except Exception as e:
        print("could not find session title under the header '" + SESSION_TITLE_KEY + "'")
        sys.exit(0)

    print(sessionTitle)
    for index, row in csvDataframe.iterrows():
        description = row["description"]
        time_range = row["time_range"]
        timeRangeSplit = time_range.split("-")
        if (len(timeRangeSplit)) == 1:
            # only single time number exists, create tuple with previous end as the start of this section
            startTime = previousEndTime
            endTime = timeRangeSplit[0]
            previousEndTime = endTime
        else:
            # both numbers exist, extract now
            startTime = timeRangeSplit[0]
            endTime = timeRangeSplit[1]
            previousEndTime = endTime

        clipName = description + "__" + audioFileNameWithoutExtension + "___" + sessionTitle

        print("clip chunk identified: " + clipName)
        #actually export the song
        if song is not None:
            startTimeSeconds = get_sec(startTime)
            startTimeMilliseconds = startTimeSeconds * 1000
            endTimeSeconds = get_sec(endTime)
            endTimeMilliseconds = endTimeSeconds * 1000

            audioFileLength = time.strftime('%H:%M:%S', time.gmtime(song.duration_seconds))
            if startTimeSeconds > song.duration_seconds:
                print("specified time " + str(startTime) + " for clip " + clipName + " is beyond the max length of the audio file " + audioFileLength)
                print("make sure you are referencing the right audio file")
                exit(0)
            if endTimeSeconds > song.duration_seconds:
                print("specified time " + str(endTime) + " for clip " + clipName + " is beyond the max length of the audio file " + audioFileLength)
                print("make sure you are referencing the right audio file")
                exit(0)

            songClip = song[startTimeMilliseconds:endTimeMilliseconds]
            clipName = clipName.replace("/", "-")
            clipNameWav = clipName + ".wav"
            listOfExportedTracks = os.listdir(exportedClipsFolderName)
            firstFileOfFolder = True
            trackSpecificFolderLocation = os.path.join(exportedClipsFolderName, description)
            print("attempting to export clip: " + clipNameWav + " into folder " + exportedClipsFolderName)
            for trackName in listOfExportedTracks:
                if description in trackName:
                    firstFileOfFolder = False
                    break
            if firstFileOfFolder:
                os.mkdir(trackSpecificFolderLocation)
            songClip.export(os.path.join(trackSpecificFolderLocation, clipNameWav), format="wav")
            print("successfully exported clip: " + clipNameWav + "!!\n")

def defineCommandLineArgumentsAndParse():
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    #the absolute folder path that contains both all the audio tracks and the content extraction template
    parser.add_argument('--folder', type=str, required=True)
    # parser.add_argument('--n', type=str, required=True) #the absolute path to the template csv we are extracting clips from
    parser.add_argument('--outputFolder', type=str, default=None)
    #whether it's podcast or music
    parser.add_argument('--contentType', type=str, default=None)
    parser.add_argument('--beepSound', type=int, default=None)
    args = parser.parse_args(sys.argv[1:])
    return args
def verifyTemplateArgument(templateAbsolutePath):
    if not os.path.isfile(templateAbsolutePath):
        print(targetTemplateFileName + " template file is not found. please make sure the file exists in the folder " + folderAbsolutePath + " to begin audio extraction process")
        exit(0)
def verifyFolderArgument(folderAbsolutePath):
    if not os.path.isdir(folderAbsolutePath):
        print(folderAbsolutePath + " does not specify a folder path. please specify a valid folder path")
        exit(0)
def verifyBeepArgument(beepSoundEffectAbsolutePath):
    if args.beepSound != None and not os.path.isfile(beepSoundEffectAbsolutePath):
        print(beepSoundEffect + " file is not found. please make sure the file exists in the folder " + folderAbsolutePath + " to begin audio extraction process")
        exit(0)

def verifyAndExtractSpeakerAudioFiles(listOfFileNames):
    speakerAudioFiles = []
    for file in listOfFileNames:
        if ".wav" in file:
            if not os.path.isfile(os.path.join(folderAbsolutePath, file)):
                print(file + " is not a valid file. please make sure the file exists in the folder " + folderAbsolutePath + " to begin audio extraction process")
                exit(0)
            speakerAudioFiles.append(file)
    return speakerAudioFiles

def configureOutputFolder(outputFolderArg):
    outputFolderAbsolutePathVar = None
    if outputFolderArg == None:
        print("output folder not specified, will use default output folder name '" + defaultOutputFolderName + "' to be generated in " + folderAbsolutePath)
        outputFolderAbsolutePathVar = os.path.join(folderAbsolutePath, defaultOutputFolderName)
    else:
        outputFolderAbsolutePathVar = os.path.join(folderAbsolutePath, args.outputFolder)
        print("output folder location specified. will generate output files in the following folder: " + outputFolderAbsolutePathVar)
    return outputFolderAbsolutePathVar

def userInputCreateOutputFolder(outputFolderAbsolutePath):
    try:
        if path.exists(outputFolderAbsolutePath):
            response = input("existing output folder found: " + outputFolderAbsolutePath + ". \n remove folder to create new one?")
            if response.lower() == "y":
                print("removing folder " + outputFolderAbsolutePath + " to start from scratch...")
                shutil.rmtree(outputFolderAbsolutePath)
            else:
                currentMilliseconds = millis = int(round(time.time() * 1000))
                outputFolderAbsolutePath = outputFolderAbsolutePath + str(currentMilliseconds)
                print("creating new folder to prevent overrwriting original with the following folder name: " + outputFolderAbsolutePath)
        os.mkdir(outputFolderAbsolutePath)
    except OSError:
        print ("Creation of the directory %s failed" % outputFolderAbsolutePath)
    else:
        print ("Successfully created the directory %s " % outputFolderAbsolutePath)


PODCAST_CONTENT_TYPE = "podcast"
MUSIC_CONTENT_TYPE = "music"
def verifyContentType(contentType):
    if contentType == None or (contentType != MUSIC_CONTENT_TYPE and contentType != PODCAST_CONTENT_TYPE):
        print("wrong type: " + str(args.contentType))
        sys.exit(0)
    return contentType

#MAIN FUNCTION-------------------------------------------------------
if __name__ == "__main__":
    args = defineCommandLineArgumentsAndParse()
    folderAbsolutePath = args.folder

    verifyFolderArgument(folderAbsolutePath)
    contentType = verifyContentType(args.contentType)

    folderName = os.path.basename(folderAbsolutePath)

    targetTemplateFileName = folderName + ".csv"
    templateAbsolutePath = os.path.join(folderAbsolutePath, targetTemplateFileName)
    verifyTemplateArgument(templateAbsolutePath)

    beepSoundEffect = "beepSound.mp3"
    beepSoundEffectAbsolutePath = os.path.join(folderAbsolutePath, beepSoundEffect)
    verifyBeepArgument(beepSoundEffectAbsolutePath)

    listOfFileNames = os.listdir(folderAbsolutePath)
    audioFileList = verifyAndExtractSpeakerAudioFiles(listOfFileNames)
    print(audioFileList)

    defaultOutputFolderName = folderName + "Output"
    outputFolderAbsolutePath = configureOutputFolder(args.outputFolder)
    userInputCreateOutputFolder(outputFolderAbsolutePath)

    episodeName = folderName

    print("\n")
    print("using template file " + targetTemplateFileName + " in folder " + folderAbsolutePath)

    print("Reading " + targetTemplateFileName + " file into memory...\n")
    csv = pd.read_csv(templateAbsolutePath, encoding="ISO-8859-1")
    csv = csv.fillna(EMPTY_STRING)
    print("Successfully read " + targetTemplateFileName + " file into memory! \n\n\n")

    trimmedEnding = "TRIMMED.wav"
    for audioFileName in audioFileList:
        trackFileAbsolutePath = os.path.join(folderAbsolutePath, audioFileName)

        print("Validating syntax of " + targetTemplateFileName + " ...\n")

        if contentType == PODCAST_CONTENT_TYPE:
            exportPodcastClips(csv, None, audioFileName, None)
        elif contentType == MUSIC_CONTENT_TYPE:
            exportMusicClips(csv, None, audioFileName, outputFolderAbsolutePath)
        print("Successfully validated syntax of " + targetTemplateFileName + "!\n\n\n")

        print("Loading " + audioFileName + " into memory...\n")
        song = AudioSegment.from_wav(trackFileAbsolutePath)
        audioFileNameWithoutExtension = os.path.splitext(audioFileName)[0]
        print(trackFileAbsolutePath)
        print("Successfully loaded " + audioFileName + " into memory!\n\n\n")

        print("Exporting audio chunk files into folder " + outputFolderAbsolutePath + "...\n")
        if contentType == PODCAST_CONTENT_TYPE:
            exportPodcastClips(csv, song, audioFileName, outputFolderAbsolutePath)
        elif contentType == MUSIC_CONTENT_TYPE:
            exportMusicClips(csv, song, audioFileNameWithoutExtension, outputFolderAbsolutePath)
        print("\nsuccessfully exported audio chunk files!")


        print("Exporting combined audio from all the exported audio chunks...")
        if contentType == PODCAST_CONTENT_TYPE:
            listOfAudioSegments = os.listdir(outputFolderAbsolutePath)
            listOfSpecificSpeakerAudioSegments = [x for x in listOfAudioSegments if audioFileName in x]
            print("LIST OF SPEAKER AUDIO: ")
            print(*listOfSpecificSpeakerAudioSegments, sep='\n')
            sortedListOfSpecificSpeakerAudioSegments = sorted(listOfSpecificSpeakerAudioSegments)
            print("SORTED LIST OF SPEAKER AUDIO: ")
            print(*sortedListOfSpecificSpeakerAudioSegments, sep='\n')
            firstAudioSegment = sortedListOfSpecificSpeakerAudioSegments[0]
            sortedListOfSpecificSpeakerAudioSegments.remove(firstAudioSegment)
            combinedAudio = AudioSegment.from_wav(os.path.join(outputFolderAbsolutePath, firstAudioSegment))
            # beepSound = AudioSegment.from_mp3(beepSoundEffectAbsolutePath)
            for audioSegment in sortedListOfSpecificSpeakerAudioSegments:
                audioFile = AudioSegment.from_wav(os.path.join(outputFolderAbsolutePath, audioSegment))
                # combinedAudio = combinedAudio + beepSound #sound separation from sections
                combinedAudio = combinedAudio + audioFile

            exportedFileName = os.path.join(outputFolderAbsolutePath, audioFileName + trimmedEnding)
            combinedAudio.export(exportedFileName, format="wav")
            print("\nsuccessfully exported combined audio file " + exportedFileName + "!")

            listOfAudioSegments = os.listdir(outputFolderAbsolutePath)
            for audioSegment in listOfAudioSegments:
                if trimmedEnding not in audioSegment:
                    fileToDeleteLocation = os.path.join(outputFolderAbsolutePath, audioSegment)
                    os.remove(fileToDeleteLocation)

    if contentType == PODCAST_CONTENT_TYPE:
        exportedFileName = os.path.join(outputFolderAbsolutePath, "COMBINED.wav")
        print("exporting combined audio into single audio file in location " + exportedFileName + "...")
        specificTrackFiles = os.listdir(outputFolderAbsolutePath)
        firstAudioSegment = specificTrackFiles[0]
        specificTrackFiles.remove(firstAudioSegment)
        combinedAudio = AudioSegment.from_wav(os.path.join(outputFolderAbsolutePath, firstAudioSegment))
        for speakerAudioFileName in specificTrackFiles:
            trackFileAbsolutePath = os.path.join(outputFolderAbsolutePath, speakerAudioFileName)
            print(trackFileAbsolutePath)
            audio = AudioSegment.from_wav(trackFileAbsolutePath)
            combinedAudio = combinedAudio.overlay(audio)
        combinedAudio.export(exportedFileName, format="wav")
        print("successfully exported combined audio at " + exportedFileName + "!!")
    elif contentType == MUSIC_CONTENT_TYPE:
        specificTrackFolders = os.listdir(outputFolderAbsolutePath)
        for specificTrackFolder in specificTrackFolders:
            specificTrackFolderAbsolutePath = os.path.join(outputFolderAbsolutePath, specificTrackFolder)
            if os.path.isdir(specificTrackFolderAbsolutePath):
                exportedFileName = os.path.join(specificTrackFolderAbsolutePath, specificTrackFolder + "_COMBINED.wav")
                print("exporting combined audio into single audio file in location " + exportedFileName + "...")
                specificTrackFiles = os.listdir(specificTrackFolderAbsolutePath)
                firstAudioSegment = specificTrackFiles[0]
                specificTrackFiles.remove(firstAudioSegment)
                combinedAudio = AudioSegment.from_wav(os.path.join(specificTrackFolderAbsolutePath, firstAudioSegment))
                for specificTrackFile in specificTrackFiles:
                    trackFileAbsolutePath = os.path.join(specificTrackFolderAbsolutePath, specificTrackFile)
                    print(trackFileAbsolutePath)
                    audio = AudioSegment.from_wav(trackFileAbsolutePath)
                    combinedAudio = combinedAudio.overlay(audio)
                combinedAudio.export(exportedFileName, format="wav")
                print("successfully exported combined audio at " + exportedFileName + "!!")
