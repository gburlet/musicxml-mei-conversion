'''
Copyright (c) 2012 Gregory Burlet

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''

from fileconverter import *
import os

class MeitoMusicXML(FileConverter):

    accidental_map = {
        's': '1',
        'ss': '2',
        'f': '-1',
        'ff': '-2'
    }

    note_type = {
        '1': 'whole',
        '2': 'half',
        '4': 'quarter',
        '8': 'eighth',
        '16': 'sixteenth',
        'long': 'long',
        'breve': 'breve'
    }


    def __init__(self, **kwargs):
        super(MeitoMusicXML, self).__init__(**kwargs)

    def convert(self):
        # read input mei file
        if hasattr(self, 'input_path'):
            self.meidoc = XmlImport.documentFromFile(self.input_path)
        else:
            self.meidoc = XmlImport.documentFromText(self.input_str)

        # begin constructing XML document
        score_timewise = etree.Element('score-timewise')

        # work title
        title = self.meidoc.getElementsByName('title')
        if title:
            title = title[0].value
            movement_title = etree.Element('movement-title')
            movement_title.text = title
            score_timewise.append(movement_title)

        # identification
        identification = etree.Element('identification')
        pers_names = self.meidoc.getElementsByName('persName')
        for p in pers_names:
            creator = etree.Element('creator')
            role = p.getAttribute('role').value
            creator.set('type', role)
            creator.text = p.value
            identification.append(creator)
        score_timewise.append(identification)

        # encoder
        encoding = etree.Element('encoding')
        application = self.meidoc.getElementsByName('application')
        if application:
            application = application[0].value
            software = etree.Element('software')
            software.text = application
            encoding.append(software)
        score_timewise.append(encoding)

        # part-list
        part_list = etree.Element('part-list')
        staff_defs = self.meidoc.getElementsByName('staffDef')
        for n, sd in enumerate(staff_defs):
            score_part = etree.Element('score-part')
            pid = 'p' + str(n)
            score_part.set('id', pid)

            part_name = etree.Element('part-name')
            name = sd.getAttribute('label.full').value
            part_name.text = name
            
            instr_def = sd.getChildrenByName('instrDef')
            if len(instr_def):
                instr_def = instr_def[0]
                score_instr = etree.Element('score-instrument')
                iid = 'i' + str(n)
                score_instr.set('id', iid)
                instr_name = etree.Element('instrument-name')
                instr_name.text = name
                score_instr.append(instr_name)

                midi_instr = etree.Element('midi-instrument')
                midi_instr.set('id', iid)
                midi_chan = etree.Element('midi-channel')
                midi_chan.text = instr_def.getAttribute('midi.channel').value
                midi_instr.append(midi_chan)
                midi_prog = etree.Element('midi-program')
                midi_prog.text = instr_def.getAttribute('midi.instrnum').value
                midi_instr.append(midi_prog)

            part_list.append(score_part)
            score_part.append(part_name)
            score_part.append(score_instr)
            score_part.append(midi_instr)

        score_timewise.append(part_list)

        # parse music data
        measures = self.meidoc.getElementsByName('measure')
        for n, m in enumerate(measures):
            measure = etree.Element('measure')
            measure.set('number', str(n+1))

            staves = m.getChildrenByName('staff')
            for s in staves:
                # translate only first layer
                l = s.getChildrenByName('layer')[0]
                events = l.getChildren()

                sd_ind = int(s.getAttribute('n').value) - 1
                pid = 'p' + str(sd_ind)
                part = etree.Element('part')
                part.set('id', pid)
                measure.append(part)

                # append part information
                attributes = etree.Element('attributes')
                sd = staff_defs[sd_ind]
                if sd.hasAttribute('ppq'):
                    ppq = sd.getAttribute('ppq').value
                    divisions = etree.Element('divisions')
                    divisions.text = ppq
                    attributes.append(divisions)

                if sd.hasAttribute('key.sig') and sd.hasAttribute('key.mode'):
                    key = etree.Element('key')

                    key_sig = sd.getAttribute('key.sig').value
                    fifths = etree.Element('fifths')
                    fifths.text = key_sig
                    key.append(fifths)

                    key_mode = sd.getAttribute('key.mode').value
                    mode = etree.Element('mode')
                    mode.text = key_mode
                    key.append(mode)

                    attributes.append(key)

                # get last score_def
                score_def = self.meidoc.lookBack(s, 'scoreDef')
                if score_def:
                    time = etree.Element('time')
                    if score_def.hasAttribute('meter.count'):
                        meter_count = score_def.getAttribute('meter.count').value
                        beats = etree.Element('beats')
                        beats.text = meter_count
                        time.append(beats)
                    if score_def.hasAttribute('meter.unit'):
                        meter_unit = score_def.getAttribute('meter.unit').value
                        beat_type = etree.Element('beat-type')
                        beat_type.text = meter_unit
                        time.append(beat_type)

                    attributes.append(time)

                # clef.shape & clef.line
                clef = etree.Element('clef')
                if sd.hasAttribute('clef.shape'):
                    clef_shape = sd.getAttribute('clef.shape').value
                    sign = etree.Element('sign')
                    sign.text = clef_shape
                    clef.append(sign)

                    if sd.hasAttribute('clef.line'):
                        clef_line = sd.getAttribute('clef.line').value
                        line = etree.Element('line')
                        line.text = clef_line
                        clef.append(line)
                attributes.append(clef)

                # tuning
                if sd.hasAttribute('tab.strings'):
                    staff_details = etree.Element('staff-details')
                    tab_strings = str(sd.getAttribute('tab.strings').value)
                    strings = tab_strings.split()
                    strings.reverse()

                    staff_lines = etree.Element('staff-lines')
                    staff_lines.text = str(len(strings))
                    staff_details.append(staff_lines)

                    for string_ind, strs in enumerate(strings):
                        staff_tuning = etree.Element('staff-tuning')
                        staff_tuning.set('line', str(string_ind+1))

                        pname = strs[:-1]
                        if pname[-1] == '#' or pname[-1] == 's':
                            tuning_alter = etree.Element('tuning-alter')
                            tuning_alter.text = '1'
                            pname = pname[:-1]
                            staff_tuning.append(tuning_alter)
                        if pname[-1] == '-' or pname[-1] == 'f':
                            tuning_alter = etree.Element('tuning-alter')
                            tuning_alter.text = '-1'
                            pname = pname[:-1]
                            staff_tuning.append(tuning_alter)

                        tuning_step = etree.Element('tuning-step')
                        tuning_step.text = pname
                        staff_tuning.append(tuning_step)

                        # musicxml is sounding pitch not written pitch like mei
                        oct = int(strs[-1]) - 1
                        tuning_octave = etree.Element('tuning-octave')
                        tuning_octave.text = str(oct)
                        staff_tuning.append(tuning_octave)

                        staff_details.append(staff_tuning)

                    attributes.append(staff_details)


                part.append(attributes)

                for e in events:
                    # notes
                    if e.getName() == 'note':
                        note = self._note_from_element(e)
                        part.append(note)
                    elif e.getName() == 'chord':
                        c_notes = e.getChildrenByName('note')
                        for c in c_notes:
                            note = self._note_from_element(c)
                            part.append(note)
                    elif e.getName() == 'rest':
                        if e.hasAttribute('dur.ges'):
                            dur_ges = e.getAttribute('dur.ges').value
                        else:
                            dur_ges = None
                        
                        if e.hasAttribute('dur'):
                            dur = e.getAttribute('dur').value
                        else:
                            dur = None

                        rest = self._create_rest(dur, dur_ges)
                        part.append(rest)
                            
            score_timewise.append(measure)

        doctype = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE score-timewise PUBLIC "-//Recordare//DTD MusicXML 2.0 Timewise//EN" "musicxml20/timewise.dtd">'
        musicxml_str = etree.tostring(score_timewise, pretty_print=True, doctype=doctype)
        fh = open(self.output_path, 'w')
        fh.write(musicxml_str)
        fh.close()

    def _create_rest(self, dur, dur_ges):
        note = etree.Element('note')

        rest = etree.Element('rest')
        note.append(rest)

        if dur:
            type = etree.Element('type')
            if dur in MeitoMusicXML.note_type:
                dur = MeitoMusicXML.note_type[dur]
            type.text = dur
            note.append(type)

        if dur_ges:
            duration = etree.Element('duration')
            duration.text = dur_ges
            note.append(duration)

        return note

    def _note_from_element(self, e):
        '''
        Create musicxml note from mei note element
        '''

        pname = e.getAttribute('pname').value
        oct = e.getAttribute('oct').value
        if e.hasAttribute('accid'):
            accid = e.getAttribute('accid').value
        elif e.hasAttribute('accid.ges'):
            accid = e.getAttribute('accid.ges').value
        else:
            accid = None

        if e.hasAttribute('tab.string'):
            string = e.getAttribute('tab.string').value
        else:
            string = None

        if e.hasAttribute('tab.fret'):
            fret = e.getAttribute('tab.fret').value
        else:
            fret = None

        note_container = e.getParent()
        if note_container.getName() != 'chord':
            note_container = e
            member_chord = False
        else:
            member_chord = True

        if note_container.hasAttribute('dur.ges'):
            dur_ges = note_container.getAttribute('dur.ges').value
        else:
            dur_ges = None
        
        if note_container.hasAttribute('dur'):
            dur = note_container.getAttribute('dur').value
        else:
            dur = None

        note = self._create_note(pname, oct, accid, dur, dur_ges, string, fret, member_chord)

        return note

    def _create_note(self, pname, oct, accid, dur, dur_ges, string=None, fret=None, member_chord=False):
        note = etree.Element('note')

        if member_chord:
            note.append(etree.Element('chord'))

        pitch = etree.Element('pitch')
        step = etree.Element('step')
        step.text = pname
        pitch.append(step)

        if accid:
            alter = etree.Element('alter')
            alter.text = MeitoMusicXML.accidental_map[accid]
            pitch.append(alter)

        octave = etree.Element('octave')
        octave.text = oct
        pitch.append(octave)
        note.append(pitch)

        if dur_ges:
            duration = etree.Element('duration')
            duration.text = dur_ges
            note.append(duration)

        if dur:
            type = etree.Element('type')
            if dur in MeitoMusicXML.note_type:
                dur = MeitoMusicXML.note_type[dur]
            type.text = dur
            note.append(type)

        if string and fret:
            notations = etree.Element('notations')
            technical = etree.Element('technical')

            xmlfret = etree.Element('fret')
            xmlfret.text = fret
            technical.append(xmlfret)

            xmlstring = etree.Element('string')
            xmlstring.text = string
            technical.append(xmlstring)

            notations.append(technical)
            note.append(notations)
        
        return note

if __name__ == '__main__':
    # parse command line arguments
    args = parser.parse_args()

    input_path = args.filein
    if not os.path.exists(input_path):
        raise ValueError('The input file does not exist')

    output_path = args.fileout

    # check file extensions are correct for this type of conversion
    _, input_ext = os.path.splitext(input_path)
    if input_ext != '.mei':
        raise ValueError('Input path must be a MEI file.')
    _, output_ext = os.path.splitext(output_path)
    if output_ext != '.xml':
        raise ValueError('Ouput path must have the file extension .xml')

    meiconv = MeitoMusicXML(input_path=input_path, output_path=output_path)
    meiconv.convert()
