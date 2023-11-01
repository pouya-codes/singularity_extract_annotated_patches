"""
Extracts patches. Currently using

|| Slide Name     || Extracted Patch Count ||
| MMRd/VOA-1099A   | 0 |
| p53abn/VOA-3088B | 0 |
| p53wt/VOA-3266C  | 0 |
| POLE/VOA-1932A   | 0 |
| Total            | 0 |

To run tests:
    (1) add the slides (symlinks) and their annotations to
auto_annotate/tests/mock/slides
auto_annotate/tests/mock/annotations
    (2) set the path of training log for the binary T/N model to log_file_location
"""
import os

import submodule_utils as utils
import extract_annotated_patches
from extract_annotated_patches import *

OUTPUT_DIR = 'extract_annotated_patches/tests/outputs'
OUTPUT_PATCH_DIR = os.path.join(OUTPUT_DIR, "patches")
ANNOTATION_DIR = 'extract_annotated_patches/tests/mock/annotations'
PATCH_PATTERN = 'annotation/subtype/slide/patch_size/magnification'
MOCK_DIR = 'extract_annotated_patches/tests/mock'
PATCH_DIR = os.path.join(MOCK_DIR, 'patches')
SLIDE_DIR = os.path.join(MOCK_DIR, 'slides')

create_slide_id = lambda path: utils.create_patch_id(path,
        utils.create_patch_pattern(default_slide_pattern))

list_to_space_sep_str = lambda l : ' '.join(map(str, l))

class MockConnection(object):
    def __init__(self):
        self.obj = None

    def send(self, obj):
        self.obj = obj
    
    def recv(self):
        return self.obj
