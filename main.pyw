import wave
from tkinter import Tk, Frame, Menu, Canvas, Scrollbar, simpledialog, filedialog
import tkinter as tk
import pyaudio
import pypiano
import os

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__))

# note list in octave with # of semitones
note_list = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
recorded_note_list = ["C", "D#", "F#", "A"]
white_list = ["C", "D", "E", "F", "G", "A", "B"]
black_list = ["C#", "D#", "F#", "G#", "A#"]


# we'll have to create a sound when we need it if the note is not in recorded_note_list


# piano class
def notetoindex(note, octave):
    # return index of note in keylist
    return note_list.index(note) + 12 * octave - 9


def findBlackKeysAroundWhite(note):
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


def onNotMoveTrack(ev):
    root.config(cursor="")


class Pianoui(Frame):

    def __init__(self):
        # dict that holds coordinates of each key with format name: (x, y, end_x, end_y)
        self.musicLength = None
        self.piano = pypiano.Piano()

        self.vbar_0 = None

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
        self.whatedited = None  # information needed by another function (note, tile, 0|1)
        self.lastTileAddYStart = None
        self.lastTileAddNote = None

        self.background = "#c7af67"

        self.whitekeycoords = {}
        self.blackkeycoords = {}
        self.keylist = []
        self.whitekeyheight = 300
        self.whitekeywidth = 70
        self.blackkeyheight = self.whitekeyheight * 2 / 3
        self.blackkeywidth = self.whitekeywidth * 2 / 3

        super().__init__()

        self.initUI()
        root.update()
        self.initCanvas()

    def initCanvas(self, length=None):

        self.keysCanvas = Canvas(root, bg='#111111', highlightthickness=0)
        # set keysCanvas size to root size
        self.keysCanvas.config(width=root.winfo_width(), height=self.whitekeyheight)
        # place keysCanvas in window

        self.trackCanvas = Canvas(root, bg=self.background, highlightthickness=0)
        self.trackCanvas.config(width=root.winfo_width(), height=root.winfo_height() - self.whitekeyheight)
        self.trackCanvas.place(x=0, y=0)

        self.rulerCanvas = Canvas(root, bg="white", highlightthickness=1, highlightbackground="black")
        self.rulerCanvas.config(width=self.rulerWidth, height=root.winfo_height() - self.whitekeyheight)
        self.rulerCanvas.place(x=0, y=-1)

        root.update()
        cheight = int(self.keysCanvas['height'])

        if length is None:
            # ask for the length of the track
            lentoad = simpledialog.askinteger("Track length", "How long do you want the track to be? (in seconds)")
            self.musicLength = lentoad
            lentoad *= 100  # second to pixel (100 pixels per second)
            lentoad -= root.winfo_height() - self.whitekeyheight  # minus the height of the trackCanvas
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

        self.drawKeys(cheight, root.winfo_height() - self.whitekeyheight)

        self.vbar_0 = 1 - (root.winfo_height() - self.whitekeyheight) / self.trackheight
        print(self.vbar_0)

        self.keysCanvas.bind("<Button-1>", self.onClickKey)
        self.trackCanvas.bind("<Button-1>", self.onClickTrack)
        self.trackCanvas.bind("<ButtonRelease-1>", self.onReleaseTrack)
        self.trackCanvas.bind("<Button-3>", self.onDeleteTrack)
        self.trackCanvas.bind("<MouseWheel>", self.track_wheel)
        self.keysCanvas.bind("<MouseWheel>", self.keys_wheel)
        self.rulerCanvas.bind("<MouseWheel>", self.track_wheel)
        self.trackCanvas.bind("<Motion>", self.onMoveTrack)
        self.keysCanvas.bind("<Motion>", onNotMoveTrack)
        self.rulerCanvas.bind("<Motion>", onNotMoveTrack)

        # bind up and down arrow keys to track
        root.bind("<Up>", self.onIncreaseTrack)
        root.bind("<Down>", self.onDecreaseTrack)

    def onIncreaseTrack(self, ev):  # increase intensity of tile
        # change x according to scroll
        ev.x += self.hbar.get()[0] * self.max_Xnote
        # change y according to scroll
        ev.y -= (1 - self.vbar.get()[1]) * self.trackheight

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
                        self.renderNote(key)  # redraw the key
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
                            self.renderNote(key)  # redraw the key
                            break
                    break

    def onDecreaseTrack(self, ev):
        # change x according to scroll
        ev.x += self.hbar.get()[0] * self.max_Xnote
        # change y according to scroll
        ev.y -= (1 - self.vbar.get()[1]) * self.trackheight

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
                        self.renderNote(key)  # redraw the key
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
                            self.renderNote(key)  # redraw the key
                            break
                    break

    def track_wheel(self, event):
        initial = self.vbar.get()[0] + ((event.delta / 120) * -100 / self.trackheight)  # moves 100 pixels per scroll
        # cast value to min and max
        if initial < 0:
            initial = 0
        if initial > self.vbar_0:
            initial = self.vbar_0
        self.globalV_scroll("moveto", initial)

    def keys_wheel(self, event):
        self.keysCanvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        self.trackCanvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def drawKeys(self, cheight, trackheight):
        # decrease of -5*whitewitdht to get the right position of the first white key (A0)
        oct_start = -5 * self.whitekeywidth
        keynum = 0
        # for 8 octaves
        for o in range(0, 9):
            if o == 8:
                # not real beauty, but last C
                self.keysCanvas.create_rectangle(oct_start + 0 * self.whitekeywidth,
                                                 cheight,
                                                 oct_start + (0 + 1) * self.whitekeywidth,
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
                                                     oct_start + (0 + 1) * self.whitekeywidth,
                                                     cheight - self.whitekeyheight,
                                                     [])

                oct_start -= 6 * self.whitekeywidth
            else:
                # draw white keys at bottom of canvas
                for i in range(0, 7):
                    k = self.keysCanvas.create_rectangle(oct_start + i * self.whitekeywidth,
                                                         cheight,
                                                         oct_start + (i + 1) * self.whitekeywidth,
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
                    self.whitekeycoords[white_list[i] + str(o)] = (oct_start + i * self.whitekeywidth,
                                                                   cheight,
                                                                   oct_start + (i + 1) * self.whitekeywidth,
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
                                                             cheight - (self.whitekeyheight - self.blackkeyheight),
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
                            self.blackkeycoords[black_list[i] + str(o)] = (oct_start + (
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
                                                             cheight - (self.whitekeyheight - self.blackkeyheight),
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
                            self.blackkeycoords[black_list[i] + str(o)] = (oct_start + (
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
                                                             cheight - (self.whitekeyheight - self.blackkeyheight),
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
                            self.blackkeycoords[black_list[i] + str(o)] = (oct_start + (
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
                                    oct_start + (2 + i) * self.whitekeywidth - self.blackkeywidth / 2,
                                    cheight - self.whitekeyheight,

                                    oct_start + (2 + i) * self.whitekeywidth + self.blackkeywidth / 2,
                                    cheight - (self.whitekeyheight - self.blackkeyheight),
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
                                self.blackkeycoords[black_list[i] + str(o)] = (oct_start + (
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
                                                             cheight - (self.whitekeyheight - self.blackkeyheight),
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
                            self.blackkeycoords[black_list[i] + str(o)] = (oct_start + (
                                    2 + i) * self.whitekeywidth - self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                                                           cheight - self.whitekeyheight,
                                                                           oct_start + (
                                                                                   2 + i) * self.whitekeywidth + self.blackkeywidth / 2 + self.blackkeywidth / displacementfactor,
                                                                           cheight - (
                                                                                   self.whitekeyheight - self.blackkeyheight),
                                                                           [])

            oct_start += self.whitekeywidth * 7

        # draw the ruler
        sec = 0
        for bar in range(root.winfo_height() - self.whitekeyheight, self.trackLength, -100):
            self.rulerCanvas.create_line(0, bar, self.rulerWidth + 1, bar, fill='#FF0000', width=1)
            # add text that is time in seconds
            self.rulerCanvas.create_text(0, bar - 10, text=str(sec), width=self.rulerWidth, fill='#000000',
                                         font=('Helvetica', 10), anchor='sw')
            sec += 1

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

        self.trackCanvas.config(yscrollcommand=self.vbar.set)
        self.trackCanvas.place(x=0, y=0, anchor=tk.NW, width=root.winfo_width(), height=trackheight)

        self.rulerCanvas.config(yscrollcommand=self.vbar.set,
                                scrollregion=(0, self.trackLength, 0, self.rulerCanvas.winfo_height()))
        self.rulerCanvas.place(x=0, y=0, anchor=tk.NW, width=self.rulerWidth, height=trackheight)

        self.max_Xnote = oct_start

    def globalH_scroll(self, *args):
        self.keysCanvas.xview(*args)
        self.trackCanvas.xview(*args)

    def globalV_scroll(self, *args):
        self.trackCanvas.yview(*args)
        self.rulerCanvas.yview(*args)
        # update the canvas
        self.trackCanvas.update()
        self.rulerCanvas.update()

    def initUI(self):
        self.master.title("Main menu")

        menubar = Menu(self.master)
        self.master.config(menu=menubar)

        filemenu = Menu(menubar)
        # add exit, load, save, export options in filemenu
        filemenu.add_command(label="Exit", command=self.onExit)
        filemenu.add_command(label="Load", command=self.onLoad)
        filemenu.add_command(label="Save", command=self.onSave)
        filemenu.add_command(label="Export", command=self.onExport)
        filemenu.add_command(label="Play", command=self.onPlay)

        menubar.add_cascade(label="File", menu=filemenu)

    def onExit(self):
        self.quit()

    def onMoveTrack(self, ev):
        # change x according to scroll
        ev.x += self.hbar.get()[0] * self.max_Xnote
        # change y according to scroll
        ev.y -= (1 - self.vbar.get()[1]) * self.trackheight

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

    def onClickKey(self, ev, ):
        # change x according to scroll
        ev.x += self.hbar.get()[0] * self.max_Xnote

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

    def onClickTrack(self, ev, ):
        print(self.tilemode)
        # change x according to scroll
        ev.x += self.hbar.get()[0] * self.max_Xnote
        # change y according to scroll
        ev.y -= (1 - self.vbar.get()[1]) * self.trackheight

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
                        self.whatedited = [key, index, 0]  # give necesssary info to edit
                    elif tile[1] - self.marginforresize < ev.y < tile[1] + self.marginforresize:
                        self.tilemode = "editing"  # set mode to editing
                        self.whatedited = [key, index, 1]  # give necesssary info to edit
                    elif tile[0] < ev.y < tile[1]:
                        self.tilemode = "moving"  # set mode to moving
                        self.whatedited = [key, index, ev.y]  # give necesssary info to move
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
                            self.whatedited = [key, index, 0]  # give necesssary info to edit
                        if tile[1] - self.marginforresize < ev.y < tile[1] + self.marginforresize:
                            print("edditing")
                            self.tilemode = "editing"  # set mode to editing
                            self.whatedited = [key, index, 1]  # give necesssary info to edit
                        elif tile[0] < ev.y < tile[1]:
                            print("moving")
                            self.tilemode = "moving"  # set mode to moving
                            self.whatedited = [key, index, ev.y]  # give necesssary info to move
                    break

        if self.tilemode == "default":
            self.tilemode = "adding"

        self.lastTileAddNote = key
        print(key)

        # if we have to create a track
        if self.tilemode == "adding":
            # create a little line on the track to show where the tile is going to be
            if key in self.blackkeycoords:
                self.trackCanvas.create_line(self.blackkeycoords[key][0], ev.y, self.blackkeycoords[key][2], ev.y,
                                             fill="black", width=1)
            elif key in self.whitekeycoords:

                x1, x2 = self.get_x1_x2(key)

                self.trackCanvas.create_line(x1, ev.y, x2, ev.y, fill="black", width=1)
            else:
                # should never happen
                print("not a key")
        # else
        elif self.tilemode == "editing":
            # nothing for now
            ...

    def onDeleteTrack(self, ev, ):
        # change x according to scroll
        ev.x += self.hbar.get()[0] * self.max_Xnote
        # change y according to scroll
        ev.y -= (1 - self.vbar.get()[1]) * self.trackheight

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

        self.deleteTile(key, ev.y)

    def onReleaseTrack(self, ev, ):
        # change x according to scroll
        ev.x += self.hbar.get()[0] * self.max_Xnote
        # change y according to scroll
        ev.y -= (1 - self.vbar.get()[1]) * self.trackheight
        # add tile if mode allows it
        if self.tilemode == "adding":
            self.addTile(self.lastTileAddYStart, ev.y, self.lastTileAddNote)
        elif self.tilemode == "editing":
            self.editTile(ev.y, *self.whatedited)
        elif self.tilemode == "moving":
            self.moveTile(ev.y, *self.whatedited)
            self.tilemode = "default"

    def moveTile(self, y, key, index, lastY):
        # move tile
        if key in self.blackkeycoords:
            toAdd = y - lastY
            coordinates = [x + toAdd for x in self.blackkeycoords[key][4][index][:2]]
            # erase old tile
            self.trackCanvas.create_rectangle(self.blackkeycoords[key][0] + 1,
                                              max(self.blackkeycoords[key][4][index][:2]) + 1,
                                              self.blackkeycoords[key][2], min(self.blackkeycoords[key][4][index][:2]),
                                              fill=self.background, width=0)
            # set new coordinates
            coordinates.append(self.blackkeycoords[key][4][index][2])
            self.blackkeycoords[key][4][index] = coordinates
            self.renderNote(key)
        elif key in self.whitekeycoords:
            toAdd = y - lastY
            coordinates = [x + toAdd for x in self.whitekeycoords[key][4][index][:2]]
            # erase old tile
            x1, x2 = self.get_x1_x2(key)
            self.trackCanvas.create_rectangle(x1 + 1, max(self.whitekeycoords[key][4][index][:2]) + 1,
                                              x2, min(self.whitekeycoords[key][4][index][:2]),
                                              fill=self.background, width=0)
            # set new coordinates
            coordinates.append(self.whitekeycoords[key][4][index][2])
            self.whitekeycoords[key][4][index] = coordinates
            self.renderNote(key)

    def addTile(self, y1, y2, note, intensity=4):
        # add rectangle on track canvas according to note, y1, y2
        # if note is in black key coords or white key coords, add rectangle
        print("add tile")
        interval = [y1, y2]
        interval.sort()
        # add intensity (1 to 8)
        interval.append(intensity)
        if note in self.blackkeycoords:
            self.blackkeycoords[note][4].append(interval)

            self.renderNote(note)

        elif note in self.whitekeycoords:
            self.whitekeycoords[note][4].append(interval)

            self.renderNote(note)
        else:
            # should never happen
            print("not a key")
        self.tilemode = "default"

    def get_x1_x2(self, note):
        around = findBlackKeysAroundWhite(note)
        if around[0] is not None:
            x1 = self.blackkeycoords[around[0] + note[1]][2]
        else:
            x1 = self.whitekeycoords[note][0]
        if around[1] is not None:
            x2 = self.blackkeycoords[around[1] + note[1]][0]
        else:
            x2 = self.whitekeycoords[note][2]

        # very only case
        if note == "A0":
            x2 -= self.rulerWidth - 2

        return x1, x2

    def renderTile(self, note, y1, y2, intensity):
        if note in self.blackkeycoords:
            self.trackCanvas.create_rectangle(self.blackkeycoords[note][0], y1, self.blackkeycoords[note][2], y2,
                                              fill="#222222")
            self.trackCanvas.create_text((self.blackkeycoords[note][0] + self.blackkeycoords[note][2]) / 2,
                                         (y1 + y2) / 2,
                                         text=str(intensity), fill="white")

        elif note in self.whitekeycoords:

            x1, x2 = self.get_x1_x2(note)
            self.trackCanvas.create_rectangle(x1, y1, x2, y2, fill="white")
            self.trackCanvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=str(intensity), fill="black")

        else:
            print("not a key")

    def renderNote(self, note):
        if "#" in note:
            for interval in self.blackkeycoords[note][4]:
                self.renderTile(note, *interval)
        else:
            for interval in self.whitekeycoords[note][4]:
                self.renderTile(note, *interval)

    def editTile(self, y2, key, index, side):
        # edit tile according to key, index, side until y
        # hide old tile with rectangle of color background
        if "#" in key:
            self.trackCanvas.create_rectangle(self.blackkeycoords[key][0] + 1,
                                              max(self.blackkeycoords[key][4][index][:2]) + 1,
                                              self.blackkeycoords[key][2], min(self.blackkeycoords[key][4][index][:2]),
                                              fill=self.background, width=0)

            # store new interval
            newinterval = [y2,
                           self.blackkeycoords[key][4][index][(side - 1) ** 2],  # 1->0 and 0->1
                           self.blackkeycoords[key][4][index][2]]

            # delete old interval
            self.blackkeycoords[key][4].pop(index)
            # add new interval by adding tile
            self.addTile(min(newinterval[:2]), max(newinterval[:2]), key, intensity=newinterval[2])

            self.tilemode = "default"
        else:
            x1, x2 = self.get_x1_x2(key)

            self.trackCanvas.create_rectangle(x1 + 1, max(self.whitekeycoords[key][4][index][:2]) + 1,
                                              x2, min(self.whitekeycoords[key][4][index][:2]),
                                              fill=self.background, width=0)

            newinterval = [y2,
                           self.whitekeycoords[key][4][index][(side - 1) ** 2],
                           self.whitekeycoords[key][4][index][2]]

            self.whitekeycoords[key][4].pop(index)
            self.addTile(min(newinterval[:2]), max(newinterval[:2]), key, intensity=newinterval[2])

            self.tilemode = "default"

    def deleteTile(self, key, y):
        # find what tile to delete
        if "#" in key:
            self.blackkeycoords[key][4].reverse()  # reverse so that we can take at first foreground tiles
            for i, interval in enumerate(self.blackkeycoords[key][4]):
                if min(interval[:2]) - 5 <= y <= max(interval[:2]) + 5:
                    # delete interval
                    self.trackCanvas.create_rectangle(self.blackkeycoords[key][0] + 1,
                                                      max(self.blackkeycoords[key][4][i][:2]) + 50,
                                                      # add some margin in order to hide little part of tile (ex. text)
                                                      self.blackkeycoords[key][2],
                                                      min(self.blackkeycoords[key][4][i][:2]) - 50,
                                                      # add some margin in order to hide little part of tile (ex. text)
                                                      fill=self.background, width=0)

                    self.blackkeycoords[key][4].pop(i)

                    self.blackkeycoords[key][4].reverse()  # reverse back
                    self.renderNote(key)
                    break
        else:
            self.whitekeycoords[key][4].reverse()
            for i, interval in enumerate(self.whitekeycoords[key][4]):
                if min(interval[:2]) <= y <= max(interval[:2]):
                    x1, x2 = self.get_x1_x2(key)

                    self.trackCanvas.create_rectangle(x1 + 1, max(self.whitekeycoords[key][4][i][:2]) + 1,
                                                      x2, min(self.whitekeycoords[key][4][i][:2]),
                                                      fill=self.background, width=0)

                    self.whitekeycoords[key][4].pop(i)

                    self.whitekeycoords[key][4].reverse()
                    self.renderNote(key)
                    break

    def onSave(self):
        filename = filedialog.asksaveasfilename(initialfile="music.pypiano",
                                                title="Select file to save your work",
                                                filetypes=[("Pypiano file", "*.pypiano)")]
                                                )

        if filename:
            if not filename.endswith(".pypiano"):
                filename += ".pypiano"
            self.loadToPypiano()
            self.piano.save(filename)

    def loadToPypiano(self):
        # set all the track note to the piano from pypiano and export to file
        # start with black keys
        self.piano = pypiano.Piano()
        self.piano.musicLength = self.musicLength
        for key in self.blackkeycoords:
            for interval in self.blackkeycoords[key][4]:
                print("hey")
                note = notetoindex(key[:2], int(key[2]))
                intensity = interval[2]

                # calculate the interval in seconds
                sides = interval[:2]
                for s, side in enumerate(sides):
                    if side >= 0:
                        side = (root.winfo_height() - self.whitekeyheight) - side
                    else:
                        side = abs(side) + (root.winfo_height() - self.whitekeyheight)
                    if side < 0:
                        side = 0
                    elif side > self.trackheight:
                        side = self.trackheight

                    side /= 100
                    sides[s] = side

                start = min(sides)
                duration = (max(sides) - min(sides))
                self.piano.addintervaltotrack(note, intensity * 2, start,
                                              duration)  # *2 because intensity is 2,4,6,8,10,12,14,16

        # then white keys
        for key in self.whitekeycoords:
            for interval in self.whitekeycoords[key][4]:
                note = notetoindex(key[0], int(key[1]))
                intensity = interval[2]

                # calculate the interval in seconds
                sides = interval[:2]
                for s, side in enumerate(sides):
                    if side >= 0:
                        side = (root.winfo_height() - self.whitekeyheight) - side
                    else:
                        side = abs(side) + (root.winfo_height() - self.whitekeyheight)
                    if side < 0:
                        side = 0
                    elif side > self.trackheight:
                        side = self.trackheight

                    side /= 100
                    sides[s] = side

                start = min(sides)
                duration = (max(sides) - min(sides))

                print("note : ", note, "intensity : ", intensity, "start : ", start, "duration : ", duration)
                self.piano.addintervaltotrack(note, intensity * 2, start,
                                              duration)  # *2 because intensity is 2,4,6,8,10,12,14,16

    def onExport(self, filename=None):
        # prompt user for file name, default is output.mp3
        if not filename:
            filename = filedialog.asksaveasfilename(initialfile="output.wav",
                                                    title="Select file to export",
                                                    filetypes=[("Audio file", "*.wav)")]
                                                    )

        if filename:
            if not filename.endswith(".wav"):
                filename += ".wav"
            self.loadToPypiano()
            self.piano.output_to_wav(filename)

    def onLoad(self):
        # load file
        # inverse as loadToPypiano()
        filename = filedialog.askopenfilename(title="Select file to load", filetypes=[("Pypiano file", "*.pypiano")])
        if filename:
            self.piano.load(filename)

            if self.piano.musicLength is not None:
                self.musicLength = self.piano.musicLength
            else:
                assert False, "No music length found in file, maybe corrupted?"

            self.initCanvas(self.musicLength)

            for key in self.piano.keys:
                note = key.note + str(key.octave)
                for interval in key.tracklist:
                    intensity = interval[0]
                    sides = [(root.winfo_height() - self.whitekeyheight) - side for side in
                             [interval[1] * 100, (interval[1] + interval[2]) * 100]]
                    sides.sort()
                    if "#" in note:
                        self.blackkeycoords[note][4].append([sides[0], sides[1], intensity])
                    else:
                        self.whitekeycoords[note][4].append([sides[0], sides[1], intensity])

            self.renderWholePiano()

    def renderWholePiano(self):
        # render the whole piano
        for note in self.blackkeycoords:
            self.renderNote(note)
        for note in self.whitekeycoords:
            self.renderNote(note)

    def onPlay(self):
        # play the piano and scroll at the same time
        self.onExport(filename="./tempPlay.wav")

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
        firstScroll = self.vbar.get()[0]

        data = wf.readframes(CHUNK)
        while len(data) > 0:
            # print("sec : ", sec)
            self.globalV_scroll("moveto",
                                max(1 - (sec / self.musicLength) - (1 - self.vbar_0), 0)  # convert sec to scroll value
                                )

            stream.write(data)
            data = wf.readframes(CHUNK)

            sec += CHUNK / wf.getframerate()

        stream.stop_stream()
        stream.close()

        self.globalV_scroll("moveto", firstScroll)

        print("done")
        p.terminate()


root = Tk()
root.attributes("-fullscreen", True)

app = Pianoui()
root.mainloop()
