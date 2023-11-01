import os
import shutil
import pytest
import numpy as np

from submodule_utils.metadata.annotation import GroovyAnnotation
from submodule_utils.metadata.slide_coords import (
        SlideCoordsMetadata, CoordsMetadata)

import extract_annotated_patches
import extract_annotated_patches.parser
from extract_annotated_patches import *
from extract_annotated_patches.tests import (
        OUTPUT_DIR, OUTPUT_PATCH_DIR, ANNOTATION_DIR,
        PATCH_PATTERN, PATCH_DIR, SLIDE_DIR,
        create_slide_id)

class MockConnection(object):
    def __init__(self):
        self.obj = None

    def send(self, obj):
        self.obj = obj
    
    def recv(self, obj):
        return self.obj

def test_extract_1(clean_output, slide_path):
    """
    Last run extracted 3286 patches
    """
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
    args_str = f"""
    from-arguments
    --patch_location {OUTPUT_PATCH_DIR}
    use-directory
    --slide_location {SLIDE_DIR}
    use-annotation
    --annotation_location {ANNOTATION_DIR}
    --slide_coords_location {slide_coords_location}
    """
    parser = extract_annotated_patches.parser.create_parser()
    config = parser.get_args(args_str.split())
    ape = AnnotatedPatchesExtractor(config)
    args = ape.produce_args([slide_path])
    slide_path, class_size_to_patch_path = args[0]
    recv_end = MockConnection()
    send_end = recv_end
    ape.extract_patch_by_annotation(slide_path, class_size_to_patch_path, send_end)
    cm = recv_end.recv()
    assert isinstance(cm, CoordsMetadata)
