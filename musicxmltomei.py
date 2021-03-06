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

class MusicXMLtoMei(FileConverter):

    # musicxml note type to mei
    note_type = {
        'whole': '1',
        'half': '2',
        'quarter': '4',
        'eighth': '8',
        'sixteenth': '16',
        'long': 'long',
        'breve': 'breve'
    }

    # musicxml integer accidentals to mei
    # integer of accidental is array index
    accidentals = [None, 's', 'ss', 'ff', 'f']

    def __init__(self, **kwargs):
        super(MusicXMLtoMei, self).__init__(**kwargs)

    def convert(self):
        if hasattr(self, 'input_path'):
            self.mxml = etree.parse(self.input_path).getroot()
        else:
            self.mxml = etree.fromstring(self.input_str)

        # convert to timewise if partwise (easier to convert to mei)
        if self.mxml.tag == 'score-partwise':
            xslt_root = etree.parse(FileConverter.to_timewise_xslt_path)
            transform = etree.XSLT(xslt_root)
            self.mxml = transform(self.mxml).getroot()

        # begin constructing mei document
        self.meidoc = MeiDocument()
        mei = MeiElement('mei')
        mei_head = MeiElement('meiHead')
        self.meidoc.setRootElement(mei)

        ###########################
        #         MetaData        #
        ###########################
        file_desc = MeiElement('fileDesc')

        xml_movement_title = self._get_text(self.mxml.find('movement-title'))
        title_stmt = self._create_title_stmt(xml_movement_title)

        identification = self.mxml.find('identification')
        xml_contributers = {}
        for c in identification.xpath('creator'):
            xml_contributers[c.attrib.get('type')] = c.text
        resp_stmt = self._create_resp_stmt(xml_contributers)
        title_stmt.addChild(resp_stmt)

        xml_encoder = self._get_text(identification.xpath('encoding/software'))
        encoding_desc = self._create_encoding_desc(xml_encoder)
        title_stmt.addChild(encoding_desc)

        # add the meta data to the MEI document
        mei.addChild(mei_head)
        mei_head.addChild(file_desc)
        file_desc.addChild(title_stmt)

        ###########################
        #           Body          #
        ###########################
        music = MeiElement('music')
        body = MeiElement('body')
        mdiv = MeiElement('mdiv')
        score = MeiElement('score')

        # scoreDef
        xml_first_part = self.mxml.xpath("measure[@number='1']/part[1]")[0]
        xml_key_fifths = self._get_text(xml_first_part.xpath("attributes/key/fifths"))
        xml_key_mode = self._get_text(xml_first_part.xpath("attributes/key/mode"))
        xml_meter = (self._get_text(xml_first_part.xpath("attributes/time/beats")),
                 self._get_text(xml_first_part.xpath("attributes/time/beat-type")))
        score_def = self._create_score_def(xml_meter, xml_key_fifths, xml_key_mode)

        # staffGrp/staffDef
        xml_parts = self.mxml.xpath('part-list/score-part')
        staff_grp = MeiElement('staffGrp')

        # keep track of musicxml partid to staffdef in mei
        map_pid_sd = {}
        for n, p in enumerate(xml_parts):
            xml_part_id = p.attrib.get('id')
            
            xml_first_part_measure = self.mxml.xpath("measure[@number='1']/part[@id='"+xml_part_id+"']/attributes")[0]
            xml_label_full = self._get_text(p.xpath("part-name"))
            xml_label_abbr = self._get_text(p.xpath("part-abbreviation"))

            # for staffDef retrieve attributes of first measure
            xml_clef_shape = self._get_text(xml_first_part_measure.xpath("clef/sign"))
            xml_ppq = self._get_text(xml_first_part_measure.xpath("divisions"))
            xml_key_fifths = self._get_text(xml_first_part_measure.xpath("key/fifths"))
            xml_key_mode = self._get_text(xml_first_part_measure.xpath("key/mode"))
            
            xml_tab_strings = xml_first_part_measure.xpath("staff-details/staff-tuning")
            strings_pitches = []
            for s in reversed(xml_tab_strings):
                tuning_step = self._get_text(s.xpath("tuning-step"))
                pitch_ind = FileConverter.pitch_classes.index(tuning_step)

                tuning_alter = s.xpath("tuning-alter")
                if tuning_alter:
                    pitch_ind = (pitch_ind + int(self._get_text(tuning_alter))) % len(FileConverter.pitch_classes)
                
                pname = FileConverter.pitch_classes[pitch_ind]

                # MEI encodes the written pitch, not the sounding pitch
                # Since guitar is written an octave above the sounding pitch to get everything
                # on one staff, transpose the sounding pitch by an octave
                oct = int(self._get_text(s.xpath("tuning-octave"))) + 1

                strings_pitches.append(pname + str(oct))

            staff_def = self._create_staff_def(str(n+1), xml_label_full, xml_label_abbr, xml_clef_shape, strings_pitches, xml_ppq, xml_key_fifths, xml_key_mode)
            map_pid_sd[xml_part_id] = staff_def

            # instruments
            xml_instr_name = self._get_text(p.xpath("score-instrument/instrument-name")).replace(' ', '_')
            xml_channel = self._get_text(p.xpath("midi-instrument/midi-channel"))
            xml_instr_num = self._get_text(p.xpath("midi-instrument/midi-program"))
            instr_def = self._create_instr_def(xml_instr_name, xml_channel, xml_instr_num)
            staff_def.addChild(instr_def)

            staff_grp.addChild(staff_def)

        # parse music data
        prev_score_def = None
        section = MeiElement('section')
        xml_measures = self.mxml.xpath("measure")
        for n, m in enumerate(xml_measures):
            measure = self._create_measure(str(n+1))

            xml_parts = m.xpath("part")

            # add in score definition if key or tempo has changed in the new measure
            xml_key_fifths = self._get_text(xml_parts[0].xpath("attributes/key/fifths"))
            xml_key_mode = self._get_text(xml_parts[0].xpath("attributes/key/mode"))
            xml_meter = (self._get_text(xml_parts[0].xpath("attributes/time/beats")),
                         self._get_text(xml_parts[0].xpath("attributes/time/beat-type")))
            score_def = self._create_score_def(xml_meter, xml_key_fifths, xml_key_mode)
            if prev_score_def is None or not self._compare_elements(prev_score_def, score_def):
                section.addChild(score_def)
                prev_score_def = score_def

            for p in xml_parts:
                xml_part_id = p.attrib.get('id')
                staff_def = map_pid_sd[xml_part_id]
                staff = self._create_staff(staff_def.getAttribute('n').getValue())
                layer = self._create_layer()

                # get notes played by the part
                notes = p.xpath("note")
                cur_chord = None
                for i, n in enumerate(notes):
                    dur_ges = self._get_text(n.xpath("duration"))
                    type = self._get_text(n.xpath("type"))
                    dur = MusicXMLtoMei.note_type.get(type)
                    if dur is None:
                        # check if there are digits in the type
                        pattern = re.compile('^([0-9]+)(.*)$')
                        match = pattern.match(type)
                        if match:
                            dur = match.group()

                    if len(n.xpath("rest")):
                        rest = self._create_rest(dur, dur_ges)
                        layer.addChild(rest)
                    else:
                        pname = self._get_text(n.xpath("pitch/step"))
                        oct = self._get_text(n.xpath("pitch/octave"))
                        accid = None
                        if n.xpath("boolean(pitch/alter)"):
                            alter = self._get_text(n.xpath("pitch/alter"))
                            accid = MusicXMLtoMei.accidentals[int(alter)]
                        sx = n.xpath("notations/technical/string")
                        string = None
                        if len(sx):
                            string = self._get_text(sx)
                        fret = None
                        fx = n.xpath("notations/technical/fret")
                        if len(fx):
                            fret = self._get_text(fx)
                        
                        next_chord_tag = False
                        # look ahead to next note
                        if i+1 < len(notes):
                            next_chord_tag = notes[i+1].xpath("boolean(chord)")

                        if next_chord_tag:
                            # a chord is beginning or continuing
                            if cur_chord is None:
                                # a chord is beginning
                                cur_chord = self._create_chord(dur, dur_ges)
                                layer.addChild(cur_chord)

                        if cur_chord is not None:
                            note = self._create_note(pname, oct, string, fret, accid)
                            cur_chord.addChild(note)
                        else:
                            note = self._create_note(pname, oct, string, fret, accid, dur=dur, dur_ges=dur_ges)
                            layer.addChild(note)

                        if not next_chord_tag:
                            cur_chord = None

                measure.addChild(staff)
                staff.addChild(layer)

            section.addChild(measure)

        # add the music data to the MEI document
        mei.addChild(music)
        music.addChild(body)
        body.addChild(mdiv)
        mdiv.addChild(score)
        score.addChild(score_def)
        score_def.addChild(staff_grp)
        score.addChild(section)

        if hasattr(self, 'output_path'):
            XmlExport.meiDocumentToFile(self.meidoc, self.output_path)
        else:
            return XmlExport.meiDocumentToText(self.meidoc)
        
    def _create_title_stmt(self, xml_title):
        '''
        Creates a mei titleStmt
        '''

        title_stmt = MeiElement('titleStmt')
        if xml_title is not None:
            title = MeiElement('title')
            title.setValue(xml_title)
            title_stmt.addChild(title)

        return title_stmt
    
    def _create_resp_stmt(self, contributers):
        '''
        Create a mei respStmt element
        '''

        resp_stmt = MeiElement('respStmt')
        for type, name in contributers.items():
            pers_name = MeiElement('persName')
            pers_name.addAttribute('role', type)
            if name is not None:
                try:
                    name = str(name)
                except UnicodeEncodeError:
                    name = name.encode('utf-8', 'replace')
                pers_name.setValue(name)
            resp_stmt.addChild(pers_name)

        return resp_stmt

    def _create_encoding_desc(self, encoder):
        '''
        Creates a mei encodingDesc element
        '''

        encoding_desc = MeiElement('encodingDesc')
        if encoder is not None:
            app_info = MeiElement('appInfo')
            application = MeiElement('application')
            application.setValue(encoder)
            encoding_desc.addChild(app_info)
            app_info.addChild(application)

        return encoding_desc

    def _create_score_def(self, meter, key_sig, key_mode):
        '''
        Creates a mei scoreDef element
        '''

        score_def = MeiElement('scoreDef')
        score_def.addAttribute('meter.count', meter[0])
        score_def.addAttribute('meter.unit', meter[1])
        score_def.addAttribute('key.sig', key_sig)
        score_def.addAttribute('key.mode', key_mode)

        return score_def

    def _create_staff_def(self, n, label_full, label_abbr, clef_shape, tab_strings, ppq, key_sig, key_mode):
        '''
        Creates a mei staffDef element
        '''

        staff_def = MeiElement('staffDef')
        staff_def.addAttribute('n', n)
        staff_def.addAttribute('label.full', label_full)
        staff_def.addAttribute('clef.shape', clef_shape)
        staff_def.addAttribute('tab.strings', ' '.join(tab_strings))
        staff_def.addAttribute('ppq', ppq)
        staff_def.addAttribute('key.sig', key_sig)
        staff_def.addAttribute('key.mode', key_mode)

        return staff_def

    def _create_instr_def(self, n, channel, instr_num):
        '''
        Creates a mei instrDef element
        '''

        instr_def = MeiElement('instrDef')
        instr_def.addAttribute('n', n)
        instr_def.addAttribute('midi.channel', channel)
        instr_def.addAttribute('midi.instrnum', instr_num)

        return instr_def

    def _create_staff(self, n):
        '''
        Creates a mei staff element
        '''

        staff = MeiElement('staff')
        staff.addAttribute('n', n)

        return staff

    def _create_layer(self, n='1'):
        '''
        Creates a mei layer element
        '''

        layer = MeiElement('layer')
        layer.addAttribute('n', n)

        return layer

    def _create_measure(self, n):
        '''
        Creates a mei measure element
        '''

        measure = MeiElement('measure')
        measure.addAttribute('n', n)

        return measure

    def _create_note(self, pname, oct, string=None, fret=None, accid=None, **kwargs):
        '''
        Creates a mei note element
        '''

        note = MeiElement('note')
        note.addAttribute('pname', pname)
        note.addAttribute('oct', oct)
        if accid is not None:
            note.addAttribute('accid', accid)
        if string:
            note.addAttribute('tab.string', string)
        if fret:
            note.addAttribute('tab.fret', fret)
        if 'dur' in kwargs:
            note.addAttribute('dur', kwargs['dur'])
        if 'dur_ges' in kwargs:
            note.addAttribute('dur.ges', kwargs['dur_ges'])

        return note

    def _create_rest(self, dur, dur_ges):
        '''
        Creates a rest element
        '''

        rest = MeiElement('rest')
        rest.addAttribute('dur', dur)
        rest.addAttribute('dur.ges', dur_ges)

        return rest

    def _create_chord(self, dur, dur_ges):
        '''
        Creates a chord element
        '''

        chord = MeiElement('chord')
        chord.addAttribute('dur', dur)
        chord.addAttribute('dur.ges', dur_ges)

        return chord

if __name__ == '__main__':
    # parse command line arguments
    args = parser.parse_args()

    input_path = args.filein
    if not os.path.exists(input_path):
        raise ValueError('The input file does not exist')

    output_path = args.fileout

    # check file extensions are correct for this type of conversion
    _, input_ext = os.path.splitext(input_path)
    if input_ext != '.xml':
        raise ValueError('Input path must be an uncompressed MusicXML file')
    _, output_ext = os.path.splitext(output_path)
    if output_ext != '.mei':
        raise ValueError('Ouput path must have the file extension .mei')

    meiconv = MusicXMLtoMei(input_path=input_path, output_path=output_path)
    meiconv.convert()
