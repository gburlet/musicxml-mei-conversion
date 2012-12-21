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

        musicxml_str = etree.tostring(score_timewise, pretty_print=True)
        fh = open(self.output_path, 'w')
        fh.write(musicxml_str)
        fh.close()

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
