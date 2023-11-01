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

def test_extract_1(clean_output, mock_data):
    """
    """
    slide_path = mock_data['POLE/VOA-1932A']['slide_path']
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
    patch_size = 1024
    args_str = f"""
    from-arguments
    --patch_location {OUTPUT_PATCH_DIR}
    use-directory
    --slide_location {SLIDE_DIR}
    use-annotation
    --annotation_location {ANNOTATION_DIR}
    --slide_coords_location {slide_coords_location}
    --patch_size {patch_size}
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

    """Check Stroma patches
    """
    annotation = mock_data['POLE/VOA-1932A']['annotation']
    area = annotation.get_area()
    extracted_coord_seq = cm.get_topleft_coords('Tumor')
    patch_files = os.listdir(class_size_to_patch_path['Tumor'][patch_size])
    assert len(patch_files) > 0
    assert len(patch_files) <= int(area['Tumor'] / (1024**2))
    assert len(extracted_coord_seq) == len(patch_files)
    for patch_file in patch_files:
        patch_name = utils.path_to_filename(patch_file)
        x, y = patch_name.split('_')
        x = int(x)
        y = int(y)
        assert annotation.points_to_label(np.array([[x, y],
                [x+patch_size, y],
                [x, y+patch_size],
                [x+patch_size, y+patch_size]])) == 'Tumor'
        assert (x, y,) in extracted_coord_seq

    extracted_coord_seq = cm.get_topleft_coords('Stroma')
    patch_files = os.listdir(class_size_to_patch_path['Stroma'][patch_size])
    assert len(patch_files) > 0
    assert len(patch_files) <= int(area['Stroma'] / (1024**2))
    assert len(extracted_coord_seq) == len(patch_files)
    for patch_file in patch_files:
        patch_name = utils.path_to_filename(patch_file)
        x, y = patch_name.split('_')
        x = int(x)
        y = int(y)
        assert annotation.points_to_label(np.array([[x, y],
                [x+patch_size, y],
                [x, y+patch_size],
                [x+patch_size, y+patch_size]])) == 'Stroma'
        assert (x, y,) in extracted_coord_seq

def test_run(clean_output, mock_data):
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
    patch_size = 1024
    args_str = f"""
    from-arguments
    --patch_location {OUTPUT_PATCH_DIR}
    use-directory
    --slide_location {SLIDE_DIR}
    use-annotation
    --annotation_location {ANNOTATION_DIR}
    --slide_coords_location {slide_coords_location}
    --patch_size {patch_size}
    """
    parser = extract_annotated_patches.parser.create_parser()
    config = parser.get_args(args_str.split())
    ape = AnnotatedPatchesExtractor(config)
    ape.run()
    scm = SlideCoordsMetadata.load(slide_coords_location)
    for slide_id in mock_data.keys():
        _, slide_name = slide_id.split('/')
        annotation = mock_data[slide_id]['annotation']
        area = annotation.get_area()

        """Test Tumor patches
        """
        extracted_coord_seq = scm.get_slide(slide_name).get_topleft_coords('Tumor')
        patch_dir = f"{OUTPUT_PATCH_DIR}/Tumor/{slide_id}/1024/40"
        patch_files = os.listdir(patch_dir)
        assert len(patch_files) > 0
        assert len(patch_files) <= int(area['Tumor'] / (1024**2))
        for patch_file in patch_files:
            patch_name = utils.path_to_filename(patch_file)
            x, y = patch_name.split('_')
            x = int(x)
            y = int(y)
            assert annotation.points_to_label(np.array([[x, y],
                    [x+patch_size, y],
                    [x, y+patch_size],
                    [x+patch_size, y+patch_size]])) == 'Tumor'
            assert (x, y,) in extracted_coord_seq

        """Test Stroma Patches
        """
        extracted_coord_seq = scm.get_slide(slide_name).get_topleft_coords('Stroma')
        patch_dir = f"{OUTPUT_PATCH_DIR}/Stroma/{slide_id}/1024/40"
        patch_files = os.listdir(patch_dir)
        assert len(patch_files) > 0
        assert len(patch_files) <= int(area['Stroma'] / (1024**2))
        for patch_file in patch_files:
            patch_name = utils.path_to_filename(patch_file)
            x, y = patch_name.split('_')
            x = int(x)
            y = int(y)
            assert annotation.points_to_label(np.array([[x, y],
                    [x+patch_size, y],
                    [x, y+patch_size],
                    [x+patch_size, y+patch_size]])) == 'Stroma'
            assert (x, y,) in extracted_coord_seq
