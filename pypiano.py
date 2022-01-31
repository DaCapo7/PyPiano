from pydub import AudioSegment
import json

note_list = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
recorded_note_list = ["C", "D#", "F#", "A"]


class KeyTrack:
    def __init__(self, index, verbose=False):
        self.index = index

        self.note = note_list[index % 12]
        self.octave = index // 12 + 1

        self.tracklist = []
        self.audioElem = {}

        if verbose:
            print("KeyTrack created : " + self.note + str(self.octave))

    def addintervaltotrack(self, intensity, position, duration):
        print(self.note, self.octave)
        # add (sound, position) to tracklist
        # intensity is the volume of the sound : ff, mf, pp
        # notes are C,Db,D,Eb,E,F,Gb,G,Ab,A,Bb,B + octave (ex : C1, Db1, ...)
        # duration is in seconds

        # check if intensity is in the list audioElem if not create it
        if intensity not in self.audioElem:
            if self.note in recorded_note_list:
                self.audioElem[intensity] = AudioSegment.from_file(
                    "piano/44.1khz16bit/" + self.note + str(self.octave) + "v" + str(intensity) + ".wav")
            else:
                index = note_list.index(self.note)
                # most proach note in recorded_note_list with note_list
                for i in recorded_note_list:
                    if note_list.index(i) - index in [-1, 1] or (self.note == "B" and i == "C"):
                        # reduce or incrase tone by one semitone
                        self.audioElem[intensity] = AudioSegment.from_file(
                            "piano/44.1khz16bit/" + i + str(self.octave) + "v" + str(intensity) + ".wav")

                        octaves = (index - note_list.index(i)) / 12
                        new_sample_rate = int(self.audioElem[intensity].frame_rate * (2.0 ** octaves))

                        self.audioElem[intensity] = self.audioElem[intensity]._spawn(self.audioElem[intensity].raw_data,
                                                                                     overrides={
                                                                                         'frame_rate': new_sample_rate})
                        break

        # self.tracklist.append((self.audioElem[intensity], position, min(duration,
        #                                                                self.audioElem[intensity].duration_seconds)))
        print(self.audioElem)
        self.tracklist.append((intensity,
                               position,
                               min(duration, self.audioElem[intensity].duration_seconds)))

        # sort the tracklist by position
        self.tracklist.sort(key=lambda x: x[1] + x[2])

    def create_track(self):

        # if no tracklist return empty track
        if len(self.tracklist) == 0:
            return AudioSegment.silent()
        # create a track of duration of the duration of the last sound in the list +  his positionin the list with list
        # format (sound, position, duration) + 1second
        notetrack = AudioSegment.silent(
            duration=self.tracklist[-1][2] * 1000 + self.tracklist[-1][1] * 1000)

        # format of soundlist is (intensity, position, duration)
        for sound in self.tracklist:
            intensity = sound[0]
            if intensity not in self.audioElem:
                if self.note in recorded_note_list:
                    self.audioElem[intensity] = AudioSegment.from_file(
                        "piano/44.1khz16bit/" + self.note + str(self.octave) + "v" + str(intensity) + ".wav")
                else:
                    index = note_list.index(self.note)
                    # most proach note in recorded_note_list with note_list
                    for i in recorded_note_list:
                        if note_list.index(i) - index in [-1, 1]:
                            # reduce or incrase tone by one semitone
                            self.audioElem[intensity] = AudioSegment.from_file(
                                "piano/44.1khz16bit/" + i + str(self.octave) + "v" + str(intensity) + ".wav")

                            octaves = (index - note_list.index(i)) / 12
                            new_sample_rate = int(self.audioElem[intensity].frame_rate * (2.0 ** octaves))

                            self.audioElem[intensity] = self.audioElem[intensity]._spawn(
                                self.audioElem[intensity].raw_data,
                                overrides={
                                    'frame_rate': new_sample_rate})
                            break

            # add sound to track at position and stop at end of duration
            notetrack = notetrack.overlay(
                self.audioElem[intensity][0:sound[2] * 1000],
                # sound[0] is the sound, sound[1] is the position, sound[2] is the duration
                position=sound[1] * 1000
            )

        return notetrack

    def __str__(self):
        # return self.note + str(self.octave) + " : " + str(self.tracklist) joined by \n
        return self.note + str(self.octave) + "\n\n" \
               + "\n".join(map(lambda x: str(x), self.tracklist))


def notetoindex(note, octave):
    # return index of note in keylist
    return note_list.index(note) + 12 * octave - 9


class Piano:
    def __init__(self, verbose=False):
        # key list of length 88 of elements of class Key
        self.keys = []
        self.musicLength = None

        # create 88 keys, begins at A0 (88 keys from A0 to C8, -3 to 85)
        print(len(range(-3, 85)))
        for i in range(-3, 85):
            self.keys.append(KeyTrack(i, verbose))

    def printkey(self, index):
        print(self.keys[index])

    def addintervaltotrack(self, index, intensity, position, duration):
        # add interval to keytrack
        self.keys[index].addintervaltotrack(intensity, position, duration)

    def indextonote(self, index):
        # return note of key
        return self.keys[index].note, self.keys[index].octave

    def create_track_of_note(self, index):
        return self.keys[index].create_track()

    def play(self):
        # make a list of the tracks of all the keys
        tracklist = []
        # make a loading bar to show progression
        for key in self.keys:
            tracklist.append(key.create_track())
            print(
                "\rCollecting keys 1/2 : " + str(int(100 * len(tracklist) / len(self.keys))) + "%   " + key.note + str(
                    key.octave),
                end="")

        print("\rCollecting keys 1/2 : " + "100%", end="")
        print()
        # make a track of length of the maximum duration of the tracklist
        allnotetrack = AudioSegment.silent(
            duration=max(
                map(
                    lambda x: x.duration_seconds * 1000, tracklist)
            ) + 100)
        # add all the tracks to the allnotetrack
        # make a loading bar to show progression
        for i, notetrack in enumerate(tracklist):
            allnotetrack = allnotetrack.overlay(notetrack)
            print("\rCombining 2/2 : " + str(int(100 * i / len(tracklist))) + "%", end="")
        print("\rLoading 2/2 : " + "100%", end="")
        print()
        return allnotetrack

    def save(self, filename):
        array_of_intervals = [str(self.musicLength)]
        for key in self.keys:
            array_of_intervals.append(key.tracklist)
            # load bar
            print("\rSaving : " + str(int(100 * len(array_of_intervals) / len(self.keys))) + "%", end="")
        print("\rSaving : " + "100%", end="")
        print()

        # save the array of intervals in a file as a json
        with open(filename, "wb") as f:
            f.write(json.dumps(array_of_intervals).encode())

        print("Saved to " + filename)

    def load(self, filename):
        # load the array of intervals from a file as a json
        with open(filename, "rb") as f:
            array_of_intervals = json.loads(f.read().decode())
            if type(array_of_intervals[0]) == str:
                self.musicLength = int(array_of_intervals[0])

            for i, key in enumerate(self.keys):
                key.tracklist = array_of_intervals[i + 1]  # +1 because the first element is the length of the music
                print("\rLoading file : " + str(int(100 * i / len(self.keys))) + "%", end="")
        print("\rLoading file : " + "100%", end="\n")
        print("File loaded")

    def output_to_wav(self, filename):
        self.play().export(filename, format="wav")
        print("Saved to " + filename)


print(notetoindex("C", 0))
