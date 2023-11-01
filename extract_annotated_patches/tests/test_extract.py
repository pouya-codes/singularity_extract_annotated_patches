import os
import shutil
import pytest
from PIL import Image
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
        create_slide_id, list_to_space_sep_str)

class MockConnection(object):
    def __init__(self):
        self.obj = None

    def send(self, obj):
        self.obj = obj
    
    def recv(self):
        return self.obj

def test_from_arguments_use_directory_annotation_1(clean_output, mock_data):
    """
    patches/Tumor/POLE/VOA-1932A/1024/40 1919
    patches/Stroma/POLE/VOA-1932A/1024/40 131

    TODO: check patch sizes
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

    annotation = mock_data['POLE/VOA-1932A']['annotation']
    area = annotation.get_area()
    """Check Tumor patches"""
    extracted_coord_seq = list(cm.get_topleft_coords('Tumor'))
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

    """Check Stroma patches"""
    extracted_coord_seq = list(cm.get_topleft_coords('Stroma'))
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

@pytest.mark.skip(reason="not finished")
def test_from_arguments_use_directory_annotation_3(clean_output, mock_data):
    """
    TODO: check patch sizes
    """
    slide_path = mock_data['POLE/VOA-1932A']['slide_path']
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
    patch_size = 1024
    resize_sizes = [512, 256]
    args_str = f"""
    from-arguments
    --patch_location {OUTPUT_PATCH_DIR}
    use-directory
    --slide_location {SLIDE_DIR}
    use-annotation
    --annotation_location {ANNOTATION_DIR}
    --slide_coords_location {slide_coords_location}
    --patch_size {patch_size}
    --resize_sizes {list_to_space_sep_str(resize_sizes)}
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

    annotation = mock_data['POLE/VOA-1932A']['annotation']
    area = annotation.get_area()
    """Check Tumor patches"""
    extracted_coord_seq = list(cm.get_topleft_coords('Tumor'))
    patch_files_512 = os.listdir(class_size_to_patch_path['Tumor'][512])
    patch_files_256 = os.listdir(class_size_to_patch_path['Tumor'][256])
    assert len(patch_files_512) > 0
    assert len(patch_files_512) <= int(area['Tumor'] / (1024**2))
    assert len(extracted_coord_seq) == len(patch_files_512)
    assert len(patch_files_256) == len(patch_files_512)
    for patch_file_256, patch_file_512 in zip(patch_files_256, patch_files_512):
        patch_name_512 = utils.path_to_filename(patch_file_512)
        patch_name_256 = utils.path_to_filename(patch_file_256)
        assert patch_name_256 == patch_name_512
        x, y = patch_name_512.split('_')
        x = int(x)
        y = int(y)
        assert annotation.points_to_label(np.array([[x, y],
                [x+patch_size, y],
                [x, y+patch_size],
                [x+patch_size, y+patch_size]])) == 'Tumor'
        assert (x, y,) in extracted_coord_seq
        
        patch_file_512 = os.path.join(class_size_to_patch_path['Tumor'][512], patch_file_512)
        patch_file_256 = os.path.join(class_size_to_patch_path['Tumor'][256], patch_file_256)
        patch_512 = Image.open(patch_file_512).convert('RGB')
        patch_256 = Image.open(patch_file_256).convert('RGB')

    # extracted_coord_seq = cm.get_topleft_coords('Stroma')
    # patch_files = os.listdir(class_size_to_patch_path['Stroma'][patch_size])
    # assert len(patch_files) > 0
    # assert len(patch_files) <= int(area['Stroma'] / (1024**2))
    # assert len(extracted_coord_seq) == len(patch_files)
    # for patch_file in patch_files:
    #     patch_name = utils.path_to_filename(patch_file)
    #     x, y = patch_name.split('_')
    #     x = int(x)
    #     y = int(y)
    #     assert annotation.points_to_label(np.array([[x, y],
    #             [x+patch_size, y],
    #             [x, y+patch_size],
    #             [x+patch_size, y+patch_size]])) == 'Stroma'
    #     assert (x, y,) in extracted_coord_seq
