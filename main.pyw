import wave
from tkinter import Tk, Frame, Menu, Canvas, Scrollbar, simpledialog, filedialog
import tkinter as tk
import pyaudio
import os
import keyboard

import pypiano
from utils.constant import *
from utils.funct import note_to_index

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__))


# piano class


def find_black_keys_around_white(note):
    # return list of black keys around white key
    # particular case for C8 and A0 (on borders)
    if note == "C8" or note == "A0":
        return [None, None]  # no black keys around C8 or A0
    note = note[0]
    if note == "C":
        return [None, "C#"]
    if note == "D":
        return ["C#", "D#"]
    if note == "E":
        return ["D#", None]
    if note == "F":
        return [None, "F#"]
    if note == "G":
        return ["F#", "G#"]
    if note == "A":
        return ["G#", "A#"]
    if note == "B":
        return ["A#", None]


def on_not_move_track(ev):
    root.config(cursor="")


def play_note(key):
    # buried for the moment, but will be used to play notes (problem = programm not responding at each key press)
    ...
    """
    audioElem = None
    note = key[:-1]
    octave = key[-1]

    if note == "B":
        octave_for_notecreation = int(octave) + 1
    else:
        octave_for_notecreation = int(octave)

    if note in recorded_note_list:
        audioElem = AudioSegment.from_file(
            "piano/flac/" + note + str(octave_for_notecreation) + "v8" + ".flac")
    else:
        index = note_list.index(note)
        # most proach note in recorded_note_list with note_list
        for i in recorded_note_list:
            if note_list.index(i) - index in [-1, 1] or (note == "B" and i == "C"):
                # reduce or incrase tone by one semitone
                audioElem = AudioSegment.from_file(
                    "piano/flac/" + i + str(octave_for_notecreation) + "v8" + ".flac")

                octaves = (index - note_list.index(i)) / 12 + (int(octave) - octave_for_notecreation)
                new_sample_rate = int(audioElem.frame_rate * (2.0 ** octaves))

                audioElem = audioElem._spawn(audioElem.raw_data,
                                             overrides={
                                                 'frame_rate': new_sample_rate})
                break

    # play audioElem
    play(audioElem)"""


class PianoUi(Frame):

    def __init__(self):
        # dict that holds coordinates of each key with format name: (x, y, end_x, end_y)
        self.last_landmark = None
        self.keyboardwidth = None
        self.musicLength = None
        self.piano = pypiano.Piano()

        self.vbar_0 = None
        self.copyData = []

        self.unity = 1 / 16 * 100  # = a Semiquaver

        self.isplaying = False
        self.rulerCanvas = None
        self.marginforresize = 8
        self.trackheight = None
        self.trackLength = None
        self.vbar = None
        self.keysCanvas = None
        self.trackCanvas = None
        self.hbar = None
        self.max_Xnote = None
        self.rulerWidth = 16

        self.tilemode = "default"  # or editing, deleting, adding. Default does nothing
        # information needed by another function (note, tile, 0|1)
        self.whatedited = None
        self.lastTileAddYStart = None
        self.lastTileAddNote = None

        self.background = "#c7af67"

        self.whitekeycoords = {}  # format name: (x, y, end_x, end_y, interval)
        self.blackkeycoords = {}  # format name: (x, y, end_x, end_y, interval)
        self.keylist = []
        self.whitekeyheight = 300
        self.whitekeywidth = 70
        self.blackkeyheight = self.whitekeyheight * 2 / 3
        self.blackkeywidth = self.whitekeywidth * 2 / 3

        super().__init__()

        self.init_ui()
        root.update()
        self.init_canvas()

    def init_canvas(self, length=None):
        # base = beat 60 for quarter note; 100 pixel per beat
        # minimal length for one tile is Semiquaver (1/16)

        self.keysCanvas = Canvas(root, bg='#111111', highlightthickness=0)
        # set keysCanvas size to root size
        self.keysCanvas.config(width=root.winfo_width(),
                               height=self.whitekeyheight)
        # place keysCanvas in window

        self.trackCanvas = Canvas(
            root, bg=self.background, highlightthickness=0)
        self.trackCanvas.config(width=root.winfo_width(
        ), height=root.winfo_height() - self.whitekeyheight)
        self.trackCanvas.place(x=0, y=0)

        self.rulerCanvas = Canvas(
            root, bg="white", highlightthickness=1, highlightbackground="black")
        self.rulerCanvas.config(
            width=self.rulerWidth, height=root.winfo_height() - self.whitekeyheight)
        self.rulerCanvas.place(x=0, y=-1)

        root.update()
        cheight = int(self.keysCanvas['height'])

        if length is None:
            # ask for the length of the track
            lentoad = simpledialog.askinteger(
                "Track length", "How long do you want the track to be? (in seconds)")
            self.musicLength = lentoad
            lentoad *= 100  # second to pixel (100 pixels per second)
            # minus the height of the trackCanvas
            lentoad -= root.winfo_height() - self.whitekeyheight
            if lentoad < 0:
                lentoad = 0
            self.trackLength = -lentoad
            self.trackheight = root.winfo_height() - self.whitekeyheight + lentoad
        else:
            self.musicLength = length
            self.trackheight = length * 100

            if self.trackheight < root.winfo_height() - self.whitekeyheight:
                self.trackheight = root.winfo_height() - self.whitekeyheight

            self.trackLength = root.winfo_height() - self.whitekeyheight - self.trackheight

        self.draw_keys(cheight, root.winfo_height() - self.whitekeyheight)

        self.vbar_0 = 1 - (root.winfo_height() -
                           self.whitekeyheight) / self.trackheight
        print(self.vbar_0)

        self.keysCanvas.bind("<Button-1>", self.on_click_key)
        self.trackCanvas.bind("<Button-1>", self.on_click_track)
        self.trackCanvas.bind("<ButtonRelease-1>", self.on_release_track)
        self.trackCanvas.bind("<Button-3>", self.on_delete_track)
        self.trackCanvas.bind("<MouseWheel>", self.track_wheel)
        self.keysCanvas.bind("<MouseWheel>", self.keys_wheel)
        self.rulerCanvas.bind("<MouseWheel>", self.track_wheel)
        self.trackCanvas.bind("<Motion>", self.on_move_track)
        self.keysCanvas.bind("<Motion>", on_not_move_track)
        self.rulerCanvas.bind("<Motion>", on_not_move_track)

        root.bind("<Control-c>", self.copy)
        root.bind("<Control-v>", self.paste)

        root.bind("<Double-space>", self.on_space)

        # bind up and down arrow keys to track
        root.bind("<Up>", self.on_increase_track)
        root.bind("<Down>", self.on_decrease_track)

    def on_space(self, event):
        if self.isplaying:
            pass
        else:
            self.on_play()

    def what_clicked(self, ev):
        ev = self.convert_event(ev)
        key = None
        clicked = None
        for i in self.blackkeycoords:
            if self.blackkeycoords[i][0] < ev.x < self.blackkeycoords[i][2]:
                key = i
                clicked = [key, None]

                for index, tile in enumerate(self.blackkeycoords[i][4]):
                    if tile[0] < ev.y < tile[1]:
                        clicked = [key, index]
                break
        # do same for white keys
        if key is None:
            for i in self.whitekeycoords:
                if self.whitekeycoords[i][0] < ev.x < self.whitekeycoords[i][2]:
                    key = i
                    clicked = [key, None]

                    # if ev.y is around one side of the key, set mode to editing and give necessary info
                    for index, tile in enumerate(self.whitekeycoords[i][4]):
                        if tile[0] < ev.y < tile[1]:
                            clicked = [key, index]
                    break

        return clicked

    def copy(self, ev):
        clicked = self.what_clicked(ev)
        if "#" in clicked[0]:
            self.copyData = [clicked[0], *
                             self.blackkeycoords[clicked[0]][4][clicked[1]]]
        else:
            self.copyData = [clicked[0], *
                             self.whitekeycoords[clicked[0]][4][clicked[1]]]
        print(self.copyData)

    def paste(self, ev):
        if self.copyData is not None and self.copyData[1] is not None:
            key = self.what_clicked(ev)[0]

            # y1, y2, key, intensity
            self.add_tile(self.copyData[1],
                          self.copyData[2], key, self.copyData[3])

    def on_increase_track(self, ev):  # increase intensity of tile
        ev = self.convert_event(ev)

        # get the key that was clicked
        # start with black keys
        key = None
        for i in self.blackkeycoords:
            if self.blackkeycoords[i][0] < ev.x < self.blackkeycoords[i][2]:
                key = i

                # if ev.y is around one side of the key, set mode to editing and give necessary info
                # also check if the tile should be moved
                for index, tile in enumerate(self.blackkeycoords[i][4]):
                    if tile[0] < ev.y < tile[1]:
                        # increase intensity of 1
                        self.blackkeycoords[i][4][index][2] += 1
                        if self.blackkeycoords[i][4][index][2] > 8:
                            self.blackkeycoords[i][4][index][2] = 1
                        self.render_note(key)  # redraw the key
                        break
                break
        # do same for white keys
        if key is None:
            for i in self.whitekeycoords:
                if self.whitekeycoords[i][0] < ev.x < self.whitekeycoords[i][2]:
                    key = i

                    # if ev.y is around one side of the key, set mode to editing and give necessary info
                    for index, tile in enumerate(self.whitekeycoords[i][4]):
                        if tile[0] < ev.y < tile[1]:
                            # increase intensity of 1
                            self.whitekeycoords[i][4][index][2] += 1
                            if self.whitekeycoords[i][4][index][2] > 8:
                                self.whitekeycoords[i][4][index][2] = 1
                            self.render_note(key)  # redraw the key
                            break
                    break

    def on_decrease_track(self, ev):
        ev = self.convert_event(ev)

        # get the key that was clicked
        # start with black keys
        key = None
        for i in self.blackkeycoords:
            if self.blackkeycoords[i][0] < ev.x < self.blackkeycoords[i][2]:
                key = i

                # if ev.y is around one side of the key, set mode to editing and give necessary info
                # also check if the tile should be moved
                for index, tile in enumerate(self.blackkeycoords[i][4]):
                    if tile[0] < ev.y < tile[1]:
                        # increase intensity of 1
                        self.blackkeycoords[i][4][index][2] -= 1
                        if self.blackkeycoords[i][4][index][2] < 1:
                            self.blackkeycoords[i][4][index][2] = 8
                        self.render_note(key)  # redraw the key
                        break
                break
        # do same for white keys
        if key is None:
            for i in self.whitekeycoords:
                if self.whitekeycoords[i][0] < ev.x < self.whitekeycoords[i][2]:
                    key = i

                    # if ev.y is around one side of the key, set mode to editing and give necessary info
                    for index, tile in enumerate(self.whitekeycoords[i][4]):
                        if tile[0] < ev.y < tile[1]:
                            # increase intensity of 1
                            self.whitekeycoords[i][4][index][2] -= 1
                            if self.whitekeycoords[i][4][index][2] < 1:
                                self.whitekeycoords[i][4][index][2] = 8
                            self.render_note(key)  # redraw the key
                            break
                    break

    def track_wheel(self, event):
        # moves 100 pixels per scroll
        initial = self.vbar.get()[0] + ((event.delta / 120)
                                        * -100 / self.trackheight)
        # cast value to min and max
        if initial < 0:
            initial = 0
        if initial > self.vbar_0:
            initial = self.vbar_0
        self.globalV_scroll("moveto", initial)

    def keys_wheel(self, event):
        self.keysCanvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        self.trackCanvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def draw_keys(self, cheight, trackheight):
        # decrease of -5*whitewitdht to get the right position of the first white key (A0)
        oct_start = -5 * self.whitekeywidth
        # for 8 octaves
        for o in range(0, 9):
            if o == 8:
                # not real beauty, but last C
                self.keysCanvas.create_rectangle(oct_start + 0 * self.whitekeywidth,
                                                 cheight,
                                                 oct_start +
                                                 (0 + 1) * self.whitekeywidth,
                                                 cheight - self.whitekeyheight,
                                                 fill='white')
                self.trackCanvas.create_line(oct_start + 0 * self.whitekeywidth,
                                             self.trackLength,
                                             oct_start + 0 * self.whitekeywidth,
                                             trackheight,
                                             fill='black',
                                             width=1)
                self.keysCanvas.create_text(oct_start + 0 * self.whitekeywidth + self.whitekeywidth / 2,
                                            cheight - self.whitekeyheight / 7,
                                            text='C8',
                                            fill='black',
                                            font=('Helvetica', 10))

                # add key to keycoords
                self.whitekeycoords["C" + str(o)] = (oct_start + 0 * self.whitekeywidth,
                                                     cheight,
                                                     oct_start +
                                                     (0 + 1) *
                                                     self.whitekeywidth,
                                                     cheight - self.whitekeyheight,
                                                     [])

                oct_start -= 6 * self.whitekeywidth
            else:
                # draw white keys at bottom of canvas
                for i in range(0, 7):
                    k = self.keysCanvas.create_rectangle(oct_start + i * self.whitekeywidth,
                                                         cheight,
                                                         oct_start +
                                                         (i + 1) *
                                                         self.whitekeywidth,
                                                         cheight - self.whitekeyheight,
                                                         fill='white')
                    if i == 0:
                        self.keysCanvas.create_text(oct_start + i * self.whitekeywidth + self.whitekeywidth / 2,
                                                    cheight - self.whitekeyheight / 7,
                                                    text='C' + str(o),
                                                    fill='black',
                                                    font=('Helvetica', 10))
                    # create vertical line at left of key that continue for 1000 pixels height only for C and F
                    if i % 7 == 0 or i % 7 == 3:
                        self.trackCanvas.create_line(oct_start + i * self.whitekeywidth,
                                                     self.trackLength,
                                                     oct_start + i * self.whitekeywidth,
                                                     trackheight,
                                                     fill='#000000',
                                                     width=1)

                    # add key to keycoords
                    self.whitekeycoords[WHITE_LIST[i] + str(o)] = (oct_start + i * self.whitekeywidth,
                                                                   cheight,
                                                                   oct_start +
                                                                   (i + 1) *
                                                                   self.whitekeywidth,
                                                                   cheight - self.whitekeyheight,
                                                                   [])

                # draw black keys and their lines at bottom of canvas
                color = "black"
                displacementfactor = 5
                for i in range(0, 5):
                    match i:
                        case 0:
                            self.keysCanvas.create_rectangle(oct_start + (
                                1 + i) * self.whitekeywidth - self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                cheight - self.whitekeyheight,

                                oct_start + (
                                i + 1) * self.whitekeywidth + self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                cheight - (self.whitekeyheight -
                                           self.blackkeyheight),
                                fill=color)

                            self.trackCanvas.create_line(oct_start + (
                                1 + i) * self.whitekeywidth - self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                self.trackLength,
                                oct_start + (
                                1 + i) * self.whitekeywidth - self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                trackheight,
                                fill='#000000',
                                width=1)
                            self.trackCanvas.create_line(oct_start + (
                                i + 1) * self.whitekeywidth + self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                self.trackLength,
                                oct_start + (
                                i + 1) * self.whitekeywidth + self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                trackheight,
                                fill='#000000',
                                width=1)

                            # add key to keycoords
                            self.blackkeycoords[BLACK_LIST[i] + str(o)] = (oct_start + (
                                1 + i) * self.whitekeywidth - self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                cheight - self.whitekeyheight,
                                oct_start + (
                                i + 1) * self.whitekeywidth + self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                cheight - (
                                self.whitekeyheight - self.blackkeyheight),
                                [])

                        case 1:
                            self.keysCanvas.create_rectangle(oct_start + (
                                1 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                cheight - self.whitekeyheight,
                                oct_start + (
                                i + 1) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                cheight - (self.whitekeyheight -
                                           self.blackkeyheight),
                                fill=color)

                            self.trackCanvas.create_line(oct_start + (
                                1 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                self.trackLength,
                                oct_start + (
                                1 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                trackheight,
                                fill='#000000',
                                width=1)
                            self.trackCanvas.create_line(oct_start + (
                                i + 1) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                self.trackLength,
                                oct_start + (
                                i + 1) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                trackheight,
                                fill='#000000',
                                width=1)

                            # add key to keycoords
                            self.blackkeycoords[BLACK_LIST[i] + str(o)] = (oct_start + (
                                1 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                cheight - self.whitekeyheight,
                                oct_start + (
                                i + 1) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                cheight - (
                                self.whitekeyheight - self.blackkeyheight),
                                [])

                        case 2:
                            self.keysCanvas.create_rectangle(oct_start + (
                                2 + i) * self.whitekeywidth - self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                cheight - self.whitekeyheight,

                                oct_start + (
                                2 + i) * self.whitekeywidth + self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                cheight - (self.whitekeyheight -
                                           self.blackkeyheight),
                                fill=color)

                            self.trackCanvas.create_line(oct_start + (
                                2 + i) * self.whitekeywidth - self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                self.trackLength,
                                oct_start + (
                                2 + i) * self.whitekeywidth - self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                trackheight,
                                fill='#000000',
                                width=1)
                            self.trackCanvas.create_line(oct_start + (
                                2 + i) * self.whitekeywidth + self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                self.trackLength,
                                oct_start + (
                                2 + i) * self.whitekeywidth + self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                trackheight,
                                fill='#000000',
                                width=1)
                            # add key to keycoords
                            self.blackkeycoords[BLACK_LIST[i] + str(o)] = (oct_start + (
                                2 + i) * self.whitekeywidth - self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                cheight - self.whitekeyheight,
                                oct_start + (
                                2 + i) * self.whitekeywidth + self.blackkeywidth / 2 - self.blackkeywidth / displacementfactor,
                                cheight - (
                                self.whitekeyheight - self.blackkeyheight),
                                [])

                        case 3:
                            if oct_start > 0:
                                self.keysCanvas.create_rectangle(
                                    oct_start +
                                    (2 + i) * self.whitekeywidth -
                                    self.blackkeywidth / 2,
                                    cheight - self.whitekeyheight,

                                    oct_start +
                                    (2 + i) * self.whitekeywidth +
                                    self.blackkeywidth / 2,
                                    cheight - (self.whitekeyheight -
                                               self.blackkeyheight),
                                    fill=color)

                                self.trackCanvas.create_line(oct_start + (
                                    2 + i) * self.whitekeywidth - self.blackkeywidth / 2,
                                    self.trackLength,
                                    oct_start + (
                                    2 + i) * self.whitekeywidth - self.blackkeywidth / 2,
                                    trackheight,
                                    fill='#000000',
                                    width=1)
                                self.trackCanvas.create_line(oct_start + (
                                    2 + i) * self.whitekeywidth + self.blackkeywidth / 2,
                                    self.trackLength,
                                    oct_start + (
                                    2 + i) * self.whitekeywidth + self.blackkeywidth / 2,
                                    trackheight,
                                    fill='#000000',
                                    width=1)
                                # add key to keycoords
                                self.blackkeycoords[BLACK_LIST[i] + str(o)] = (oct_start + (
                                    2 + i) * self.whitekeywidth - self.blackkeywidth / 2,
                                    cheight - self.whitekeyheight,
                                    oct_start + (
                                    2 + i) * self.whitekeywidth + self.blackkeywidth / 2,
                                    cheight - (
                                    self.whitekeyheight - self.blackkeyheight),
                                    [])

                        case 4:
                            self.keysCanvas.create_rectangle(oct_start + (
                                2 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                cheight - self.whitekeyheight,

                                oct_start + (
                                2 + i) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                cheight - (self.whitekeyheight -
                                           self.blackkeyheight),
                                fill=color)

                            self.trackCanvas.create_line(oct_start + (
                                2 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                self.trackLength,
                                oct_start + (
                                2 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                trackheight,
                                fill='#000000',
                                width=1)
                            self.trackCanvas.create_line(oct_start + (
                                2 + i) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                self.trackLength,
                                oct_start + (
                                2 + i) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                trackheight,
                                fill='#000000',
                                width=1)
                            # add key to keycoords
                            self.blackkeycoords[BLACK_LIST[i] + str(o)] = (oct_start + (
                                2 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                cheight - self.whitekeyheight,
                                oct_start + (
                                2 + i) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                cheight - (
                                self.whitekeyheight - self.blackkeyheight),
                                [])

            oct_start += self.whitekeywidth * 7
        # removes 5 first elements of whitekeycoords because we don't need them
        for i in ["C0", "D0", "E0", "F0", "G0"]:
            del self.whitekeycoords[i]

        print(self.whitekeycoords)
        # draw the ruler
        self.load_ruler()

        # make the canvas scrollable on x
        self.hbar = Scrollbar(self.keysCanvas, orient="horizontal")
        self.hbar.pack(side="bottom", fill="x")
        self.hbar.config(command=self.globalH_scroll)

        self.vbar = Scrollbar(self.trackCanvas, orient="vertical")
        self.vbar.pack(side="right", fill="y")
        self.vbar.config(command=self.globalV_scroll)

        # place the canvas in the root window and resize it to fit the root window at the bottom
        self.keysCanvas.config(xscrollcommand=self.hbar.set,
                               scrollregion=(0, 0, oct_start, self.keysCanvas.winfo_height()))
        self.keysCanvas.place(x=0, y=root.winfo_height() - self.whitekeyheight, anchor=tk.NW, width=root.winfo_width(),
                              height=self.whitekeyheight)

        self.trackCanvas.config(xscrollcommand=self.hbar.set,
                                scrollregion=(0, self.trackLength, oct_start, self.trackCanvas.winfo_height()))
        self.keyboardwidth = oct_start
        self.trackCanvas.config(yscrollcommand=self.vbar.set)
        self.trackCanvas.place(x=0, y=0, anchor=tk.NW,
                               width=root.winfo_width(), height=trackheight)

        self.rulerCanvas.config(yscrollcommand=self.vbar.set,
                                scrollregion=(0, self.trackLength, 0, self.rulerCanvas.winfo_height()))
        self.rulerCanvas.place(x=0, y=0, anchor=tk.NW,
                               width=self.rulerWidth, height=trackheight)

        self.max_Xnote = oct_start

    def load_ruler(self):
        sec = 0
        self.rulerCanvas.create_rectangle(0, self.rulerCanvas.winfo_height(), self.rulerWidth, self.trackLength,
                                          fill='#FFFFFF')
        for bar in range(root.winfo_height() - self.whitekeyheight, self.trackLength, -100):
            self.rulerCanvas.create_line(
                0, bar, self.rulerWidth + 1, bar, fill='#FF0000', width=1)
            # add text that is time in seconds
            self.rulerCanvas.create_text(0, bar - 10, text=str(sec), width=self.rulerWidth, fill='#000000',
                                         font=('Helvetica', 10), anchor='sw')
            sec += 1

    def globalH_scroll(self, *args):
        self.keysCanvas.xview(*args)
        self.trackCanvas.xview(*args)

    def globalV_scroll(self, *args):
        self.trackCanvas.yview(*args)
        self.rulerCanvas.yview(*args)
        # update the canvas
        self.trackCanvas.update()
        self.rulerCanvas.update()

    def init_ui(self):
        self.master.title("Main menu")

        menubar = Menu(self.master)
        self.master.config(menu=menubar)

        filemenu = Menu(menubar)
        # add exit, load, save, export options in filemenu
        filemenu.add_command(label="Exit", command=self.on_exit)
        filemenu.add_command(label="Load", command=self.on_load)
        filemenu.add_command(label="Save", command=self.on_save)
        filemenu.add_command(label="Export", command=self.on_export)
        filemenu.add_command(label="Play (double space)", command=self.on_play)

        menubar.add_cascade(label="File", menu=filemenu)

    def on_exit(self):
        self.quit()

    def on_move_track(self, ev):
        ev = self.convert_event(ev)

        key = None
        mode = "adding"
        #  check if mouse is on border of tile, on tile or on nothing
        for i in self.blackkeycoords:
            if self.blackkeycoords[i][0] < ev.x < self.blackkeycoords[i][2]:
                key = i
                # if ev.y is around one side of the key, set mode to editing and give necessary info
                # also check if the tile should be moved
                for index, tile in enumerate(self.blackkeycoords[i][4]):
                    if tile[0] - self.marginforresize < ev.y < tile[0] + self.marginforresize or tile[
                            1] - self.marginforresize < ev.y < tile[1] + self.marginforresize:
                        mode = "editing"
                    elif tile[0] < ev.y < tile[1]:
                        mode = "moving"
                break
        # do same for white keys
        if key is None:
            for i in self.whitekeycoords:
                if self.whitekeycoords[i][0] < ev.x < self.whitekeycoords[i][2]:
                    key = i

                    # if ev.y is around one side of the key, set mode to editing and give necessary info
                    for index, tile in enumerate(self.whitekeycoords[i][4]):
                        if tile[0] - self.marginforresize < ev.y < tile[0] + self.marginforresize or tile[
                                1] - self.marginforresize < ev.y < tile[1] + self.marginforresize:
                            mode = "editing"
                        elif tile[0] < ev.y < tile[1]:
                            mode = "moving"
                    break

        if mode == "adding" or mode == "default":
            root.config(cursor="crosshair")
        elif mode == "editing":
            root.config(cursor="double_arrow")
        elif mode == "moving":
            root.config(cursor="fleur")

        if self.tilemode == "adding":
            ev.y = self.make_pixel_aligned(ev.y)
            self.just_draw_note_preview(ev.y, self.lastTileAddNote)

    def just_draw_note_preview(self, y, note):
        y1 = y
        y2 = self.lastTileAddYStart

        if note in self.blackkeycoords:
            print("black key")
            self.render_note(note)
            self.rendre_tile(note, y1, y2, 4)

        elif note in self.whitekeycoords:
            print("white key")
            self.render_note(note)
            self.rendre_tile(note, y1, y2, 4)

    def on_click_key(self, ev, ):
        ev = self.convert_event(ev)

        # get the key that was clicked
        # start with black keys
        key = None
        for i in self.blackkeycoords:
            if self.blackkeycoords[i][0] < ev.x < self.blackkeycoords[i][2] and self.blackkeycoords[i][1] < ev.y < \
                    self.blackkeycoords[i][3]:
                key = i
                break
        # do same for white keys
        if key is None:
            for i in self.whitekeycoords:
                if self.whitekeycoords[i][0] < ev.x < self.whitekeycoords[i][2]:
                    key = i
                    break

        print(key)
        # play the note
        if key is not None:
            play_note(key)

    def convert_event(self, ev):
        # change x according to scroll
        ev.x += self.hbar.get()[0] * self.max_Xnote
        # change y according to scroll
        ev.y -= (1 - self.vbar.get()[1]) * self.trackheight

        return ev

    def on_click_track(self, ev, ):
        print(self.tilemode)

        ev = self.convert_event(ev)

        self.lastTileAddYStart = ev.y
        # get the key that was clicked
        # start with black keys
        key = None
        for i in self.blackkeycoords:
            if self.blackkeycoords[i][0] < ev.x < self.blackkeycoords[i][2]:
                key = i

                # if ev.y is around one side of the key, set mode to editing and give necessary info
                # also check if the tile should be moved
                for index, tile in enumerate(self.blackkeycoords[i][4]):
                    if tile[0] - self.marginforresize < ev.y < tile[0] + self.marginforresize:
                        self.tilemode = "editing"  # set mode to editing
                        # give necesssary info to edit
                        self.whatedited = [key, index, 0]
                    elif tile[1] - self.marginforresize < ev.y < tile[1] + self.marginforresize:
                        self.tilemode = "editing"  # set mode to editing
                        # give necesssary info to edit
                        self.whatedited = [key, index, 1]
                    elif tile[0] < ev.y < tile[1]:
                        self.tilemode = "moving"  # set mode to moving
                        # give necesssary info to move
                        self.whatedited = [key, index, ev.y]
                break
        # do same for white keys
        if key is None:
            for i in self.whitekeycoords:
                if self.whitekeycoords[i][0] < ev.x < self.whitekeycoords[i][2]:
                    key = i

                    # if ev.y is around one side of the key, set mode to editing and give necessary info
                    for index, tile in enumerate(self.whitekeycoords[i][4]):
                        if tile[0] - self.marginforresize < ev.y < tile[0] + self.marginforresize:
                            print("editing")
                            self.tilemode = "editing"  # set mode to editing
                            # give necesssary info to edit
                            self.whatedited = [key, index, 0]
                        if tile[1] - self.marginforresize < ev.y < tile[1] + self.marginforresize:
                            print("edditing")
                            self.tilemode = "editing"  # set mode to editing
                            # give necesssary info to edit
                            self.whatedited = [key, index, 1]
                        elif tile[0] < ev.y < tile[1]:
                            print("moving")
                            self.tilemode = "moving"  # set mode to moving
                            # give necesssary info to move
                            self.whatedited = [key, index, ev.y]
                    break

        if self.tilemode == "default":
            self.tilemode = "adding"

        self.lastTileAddNote = key
        print(key)

        # if we have to create a track
        if self.tilemode == "adding":
            # align y
            ev.y = self.make_pixel_aligned(ev.y)
            # create a little line on the track to show where the tile is going to be
            if key in self.blackkeycoords:
                self.trackCanvas.create_line(self.blackkeycoords[key][0], ev.y, self.blackkeycoords[key][2], ev.y,
                                             fill="black", width=1)
            elif key in self.whitekeycoords:

                x1, x2 = self.get_x1_x2_whitekey(key)

                self.trackCanvas.create_line(
                    x1, ev.y, x2, ev.y, fill="black", width=1)
            else:
                # should never happen
                print("not a key")
        # else
        elif self.tilemode == "editing":
            # nothing for now
            ...

    def on_delete_track(self, ev, ):
        ev = self.convert_event(ev)

        key = None
        for i in self.blackkeycoords:
            if self.blackkeycoords[i][0] < ev.x < self.blackkeycoords[i][2]:
                key = i
                break
        # do same for white keys
        if key is None:
            for i in self.whitekeycoords:
                if self.whitekeycoords[i][0] < ev.x < self.whitekeycoords[i][2]:
                    key = i
                    break

        self.delete_tile(key, ev.y)

    def on_release_track(self, ev, ):
        ev = self.convert_event(ev)
        # add tile if mode allows it
        if self.tilemode == "adding":
            self.add_tile(self.lastTileAddYStart, ev.y, self.lastTileAddNote)
        elif self.tilemode == "editing":
            self.edit_tile(ev.y, *self.whatedited)
        elif self.tilemode == "moving":
            self.move_tile(ev.y, *self.whatedited)
            self.tilemode = "default"

    def move_tile(self, y, key, index, lastY):
        # align y and lastY
        y = self.make_pixel_aligned(y)
        lastY = self.make_pixel_aligned(lastY)
        # move tile
        if key in self.blackkeycoords:
            toAdd = y - lastY
            coordinates = [
                x + toAdd for x in self.blackkeycoords[key][4][index][:2]]
            # erase old tile
            self.trackCanvas.create_rectangle(self.blackkeycoords[key][0] + 1,
                                              max(self.blackkeycoords[key]
                                                  [4][index][:2]) + 1,
                                              self.blackkeycoords[key][2], min(
                                                  self.blackkeycoords[key][4][index][:2]),
                                              fill=self.background, width=0)
            # set new coordinates
            coordinates.append(self.blackkeycoords[key][4][index][2])
            self.blackkeycoords[key][4][index] = coordinates
            self.render_note(key)
        elif key in self.whitekeycoords:
            toAdd = y - lastY
            coordinates = [
                x + toAdd for x in self.whitekeycoords[key][4][index][:2]]
            # erase old tile
            x1, x2 = self.get_x1_x2_whitekey(key)
            self.trackCanvas.create_rectangle(x1 + 1, max(self.whitekeycoords[key][4][index][:2]) + 1,
                                              x2, min(
                                                  self.whitekeycoords[key][4][index][:2]),
                                              fill=self.background, width=0)
            # set new coordinates
            coordinates.append(self.whitekeycoords[key][4][index][2])
            self.whitekeycoords[key][4][index] = coordinates
            self.render_note(key)

    def make_pixel_aligned(self, y):
        # make y the nearest multiple of self.unity
        return round(y / self.unity) * self.unity

    def add_tile(self, y1, y2, note, intensity=4):
        # add rectangle on track canvas according to note, y1, y2
        # if note is in black key coords or white key coords, add rectangle
        # make sure y1 and y2 are pixel aligned
        y1 = self.make_pixel_aligned(y1)
        y2 = self.make_pixel_aligned(y2)

        print("add tile")
        interval = [y1, y2]
        interval.sort()
        # add intensity (1 to 8)
        interval.append(intensity)
        if note in self.blackkeycoords:
            print("black key")
            self.blackkeycoords[note][4].append(interval)

            self.render_note(note)

        elif note in self.whitekeycoords:
            print("white key")
            self.whitekeycoords[note][4].append(interval)

            self.render_note(note)
        else:
            # should never happen
            print("not a key")
        self.tilemode = "default"

    def get_x1_x2_whitekey(self, note):
        around = find_black_keys_around_white(note)
        if around[0] is not None:
            x1 = self.blackkeycoords[around[0] + note[1]][2]
        else:
            x1 = self.whitekeycoords[note][0]
        if around[1] is not None:
            print(note, around)
            x2 = self.blackkeycoords[around[1] + note[1]][0]
        else:
            x2 = self.whitekeycoords[note][2]

        # very only case
        if note == "A0":
            x2 -= self.rulerWidth - 2

        return x1, x2

    def rendre_tile(self, note, y1, y2, intensity):
        if note in self.blackkeycoords:
            self.trackCanvas.create_rectangle(self.blackkeycoords[note][0], y1, self.blackkeycoords[note][2], y2,
                                              fill="#222222")
            self.trackCanvas.create_text((self.blackkeycoords[note][0] + self.blackkeycoords[note][2]) / 2,
                                         (y1 + y2) / 2,
                                         text=str(intensity), fill="white")

        elif note in self.whitekeycoords:

            x1, x2 = self.get_x1_x2_whitekey(note)
            self.trackCanvas.create_rectangle(x1, y1, x2, y2, fill="white")
            self.trackCanvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2, text=str(intensity), fill="black")

        else:
            print("not a key")

    def render_note(self, note):
        if "#" in note:
            self.trackCanvas.create_rectangle(self.blackkeycoords[note][0], root.winfo_height() - self.whitekeyheight,
                                              self.blackkeycoords[note][2], self.trackLength,
                                              fill=self.background)
            for interval in self.blackkeycoords[note][4]:
                self.rendre_tile(note, *interval)
        else:
            x1, x2 = self.get_x1_x2_whitekey(note)
            self.trackCanvas.create_rectangle(x1, root.winfo_height() - self.whitekeyheight,
                                              x2, self.trackLength,
                                              fill=self.background)
            for interval in self.whitekeycoords[note][4]:
                self.rendre_tile(note, *interval)

    def edit_tile(self, y2, key, index, side):
        # align y2
        y2 = self.make_pixel_aligned(y2)
        # edit tile according to key, index, side until y
        # hide old tile with rectangle of color background
        if "#" in key:
            self.trackCanvas.create_rectangle(self.blackkeycoords[key][0] + 1,
                                              max(self.blackkeycoords[key]
                                                  [4][index][:2]) + 1,
                                              self.blackkeycoords[key][2], min(
                                                  self.blackkeycoords[key][4][index][:2]),
                                              fill=self.background, width=0)

            # store new interval
            newinterval = [y2,
                           self.blackkeycoords[key][4][index][(
                               side - 1) ** 2],  # 1->0 and 0->1
                           self.blackkeycoords[key][4][index][2]]

            # delete old interval
            self.blackkeycoords[key][4].pop(index)
            # add new interval by adding tile
            self.add_tile(min(newinterval[:2]), max(
                newinterval[:2]), key, intensity=newinterval[2])

            self.tilemode = "default"
        else:
            x1, x2 = self.get_x1_x2_whitekey(key)

            self.trackCanvas.create_rectangle(x1 + 1, max(self.whitekeycoords[key][4][index][:2]) + 1,
                                              x2, min(
                                                  self.whitekeycoords[key][4][index][:2]),
                                              fill=self.background, width=0)

            newinterval = [y2,
                           self.whitekeycoords[key][4][index][(side - 1) ** 2],
                           self.whitekeycoords[key][4][index][2]]

            self.whitekeycoords[key][4].pop(index)
            self.add_tile(min(newinterval[:2]), max(
                newinterval[:2]), key, intensity=newinterval[2])

            self.tilemode = "default"

    def delete_tile(self, key, y):
        # find what tile to delete
        if "#" in key:
            # reverse so that we can take at first foreground tiles
            self.blackkeycoords[key][4].reverse()
            for i, interval in enumerate(self.blackkeycoords[key][4]):
                if min(interval[:2]) - 5 <= y <= max(interval[:2]) + 5:
                    # delete interval
                    self.trackCanvas.create_rectangle(self.blackkeycoords[key][0] + 1,
                                                      max(self.blackkeycoords[key]
                                                          [4][i][:2]) + 50,
                                                      # add some margin in order to hide little part of tile (ex. text)
                                                      self.blackkeycoords[key][2],
                                                      min(self.blackkeycoords[key]
                                                          [4][i][:2]) - 50,
                                                      # add some margin in order to hide little part of tile (ex. text)
                                                      fill=self.background, width=0)

                    self.blackkeycoords[key][4].pop(i)

                    self.blackkeycoords[key][4].reverse()  # reverse back
                    self.render_note(key)
                    break
        else:
            self.whitekeycoords[key][4].reverse()
            for i, interval in enumerate(self.whitekeycoords[key][4]):
                if min(interval[:2]) <= y <= max(interval[:2]):
                    x1, x2 = self.get_x1_x2_whitekey(key)

                    self.trackCanvas.create_rectangle(x1 + 1, max(self.whitekeycoords[key][4][i][:2]) + 1,
                                                      x2, min(
                                                          self.whitekeycoords[key][4][i][:2]),
                                                      fill=self.background, width=0)

                    self.whitekeycoords[key][4].pop(i)

                    self.whitekeycoords[key][4].reverse()
                    self.render_note(key)
                    break

    def on_save(self, filename=None):
        if filename == None:
            filename = filedialog.asksaveasfilename(initialfile="music.pypiano",
                                                    title="Select file to save your work",
                                                    filetypes=[
                                                        ("Pypiano file", "*.pypiano)")]
                                                    )

        if filename:
            if not filename.endswith(".pypiano"):
                filename += ".pypiano"
            self.load_to_pypiano()
            self.piano.save(filename)

        filename = None

    def load_to_pypiano(self):
        # set all the track note to the piano from pypiano and export to file
        # start with black keys
        self.piano.reset_tracks()
        self.piano.musicLength = self.musicLength
        for key in self.blackkeycoords:
            for interval in self.blackkeycoords[key][4]:
                print("hey")
                note = note_to_index(NOTE_LIST, key[:2], int(key[2]))
                intensity = interval[2]

                # calculate the interval in seconds
                sides = interval[:2]
                for s, side in enumerate(sides):
                    if side >= 0:
                        side = (root.winfo_height() -
                                self.whitekeyheight) - side
                    else:
                        side = abs(side) + (root.winfo_height() -
                                            self.whitekeyheight)
                    if side < 0:
                        side = 0
                    elif side > self.trackheight:
                        side = self.trackheight

                    side /= 100
                    sides[s] = side

                start = min(sides)
                duration = (max(sides) - min(sides))
                self.piano.add_interval_to_track(note, intensity * 2, start,
                                                 duration)  # *2 because intensity is 2,4,6,8,10,12,14,16

        # then white keys
        for key in self.whitekeycoords:
            for interval in self.whitekeycoords[key][4]:
                note = note_to_index(NOTE_LIST, key[0], int(key[1]))
                intensity = interval[2]

                # calculate the interval in seconds
                sides = interval[:2]
                for s, side in enumerate(sides):
                    if side >= 0:
                        side = (root.winfo_height() -
                                self.whitekeyheight) - side
                    else:
                        side = abs(side) + (root.winfo_height() -
                                            self.whitekeyheight)
                    if side < 0:
                        side = 0
                    elif side > self.trackheight:
                        side = self.trackheight

                    side /= 100
                    sides[s] = side

                start = min(sides)
                duration = (max(sides) - min(sides))

                print("note : ", note, "intensity : ", intensity,
                      "start : ", start, "duration : ", duration)
                self.piano.add_interval_to_track(note, intensity * 2, start,
                                                 duration)  # *2 because intensity is 2,4,6,8,10,12,14,16

    def on_export(self, filename=None):
        # prompt user for file name, default is output.mp3
        if not filename:
            filename = filedialog.asksaveasfilename(initialfile="output.wav",
                                                    title="Select file to export",
                                                    filetypes=[
                                                        ("Audio file", "*.wav)")]
                                                    )

        if filename:
            if not filename.endswith(".wav"):
                filename += ".wav"
            self.load_to_pypiano()
            self.piano.output_to_wav(filename)

    def on_load(self, filename=None):
        # load file
        # inverse as loadToPypiano()
        if filename is None:
            filename = filedialog.askopenfilename(title="Select file to load", filetypes=[
                                                  ("Pypiano file", "*.pypiano")])
        if filename:
            self.piano.load(filename)

            if self.piano.musicLength is not None:
                self.musicLength = self.piano.musicLength
            else:
                assert False, "No music length found in file, maybe corrupted?"

            self.init_canvas(self.musicLength)

            for key in self.piano.keys:
                note = key.note + str(key.octave)
                for interval in key.tracklist:
                    # because intensity is 2,4,6,8,10,12,14,16
                    intensity = int(interval[0] / 2)
                    sides = [(root.winfo_height() - self.whitekeyheight) - side for side in
                             [interval[1] * 100, (interval[1] + interval[2]) * 100]]
                    sides.sort()
                    if "#" in note:
                        self.blackkeycoords[note][4].append(
                            [sides[0], sides[1], intensity])
                    else:
                        self.whitekeycoords[note][4].append(
                            [sides[0], sides[1], intensity])

            self.render_whole_piano()

        filename = None

    def render_whole_piano(self):
        # render the whole piano
        for note in self.blackkeycoords:
            self.render_note(note)
        for note in self.whitekeycoords:
            self.render_note(note)

    def on_play(self):
        hbar_pos = self.hbar.get()[0]

        # this is needed in order to have a smooth music (any other solution?) : to trigger the bug, remove theses 3 lines, make a music with +10 notes and play it
        self.on_save("temp.pypiano")
        self.on_load("temp.pypiano")

        # update canvas
        self.trackCanvas.update()
        self.globalH_scroll("moveto", hbar_pos)

        # play the piano and scroll at the same time
        self.isplaying = True
        self.on_export(filename="./tempPlay.wav")

        wf = wave.open("./tempPlay.wav", 'rb')
        p = pyaudio.PyAudio()

        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        # one frame per one frame
        CHUNK = 1024

        # skip music that is before the current scroll :
        sec = (1 - self.vbar.get()[1]) * self.musicLength
        wf.readframes(int(sec * wf.getframerate()))

        # save first scroll position
        #self.globalH_scroll("moveto", 1- firstScroll)

        data = wf.readframes(CHUNK)

        while len(data) > 0:
            # print("sec : ", sec)
            if keyboard.is_pressed("space"):
                break
            if self.trackLength != 0:
                # convert sec to scroll value
                to = max(1 - (sec / self.musicLength) - (1 - self.vbar_0), 0)
            else:
                to = 0
            self.globalV_scroll("moveto", to)
            if to == 0:
                to = self.rulerCanvas.winfo_height() - sec * 100
                self.rulerCanvas.create_rectangle(0, self.rulerCanvas.winfo_height(), self.rulerCanvas.winfo_width(),
                                                  to,
                                                  fill="red")

            stream.write(data)  # play stream
            data = wf.readframes(CHUNK)

            sec += CHUNK / wf.getframerate()

        stream.stop_stream()
        stream.close()
        self.globalV_scroll("moveto", 1)
        print("done")
        p.terminate()
        self.load_ruler()
        self.isplaying = False


root = Tk()
root.attributes("-fullscreen", True)

app = PianoUi()
root.mainloop()
