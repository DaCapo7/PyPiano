def note_to_index(note_list,note, octave):
    # return index of note in keylist
    return note_list.index(note) + 12 * octave - 9