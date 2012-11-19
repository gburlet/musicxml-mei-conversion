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

import re
from lxml import etree
from pymei import MeiDocument, MeiElement, XmlExport

import argparse

# set up command line argument structure
parser = argparse.ArgumentParser(description='Convert a MEI to MusicXML or MusicXML to MEI.')
parser.add_argument('filein', help='input file')
parser.add_argument('fileout', help='output file')
parser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')

class FileConverter(object):
    
    to_timewise_xslt_path = '/Users/gburlet/University/MA/musicxmlmeiconversion/partwisetotimewise.xslt'
    pitch_classes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(self, **kwargs):
        # for file in, file out scenarios
        if 'input_path' in kwargs:
            self.input_path = kwargs['input_path']
        elif 'input_str' in kwargs:
            self.input_str = kwargs['input_str']
        else:
            raise ValueError('Some input is needed to process.')

        if 'output_path' in kwargs:
            self.output_path = kwargs['output_path']

    def _get_text(self, element):
        '''
        Helper method to get the text of an element 
        returned by an xpath query
        '''

        if element is not None:
            return element.text

    def _compare_elements(self, e1, e2):
        '''
        Helper method to compare equality of elements,
        from element name to attributes.
        '''

        if e1.getName() != e2.getName() or len(e1.getAttributes()) != len(e2.getAttributes()):
            return False

        e1_attrs = {}
        for a in e1.getAttributes():
            e1_attrs[a.getName()] = a.getValue()
        for a in e2.getAttributes():
            e1_attr_val = e1_attrs.get(a.getName())
            if e1_attr_val is None or e1_attr_val != a.getValue(): # relies on short circuit to not throw exception
                return False

        return True
