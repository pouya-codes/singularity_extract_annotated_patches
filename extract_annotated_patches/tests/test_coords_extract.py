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
        PATCH_PATTERN, PATCH_DIR, SLIDE_DIR, MOCK_DIR,
        create_slide_id, list_to_space_sep_str,
        MockConnection)

def test_from_arguments_use_directory_slide_coords_1(clean_output, mock_data):
    """
    patches/Tumor/POLE/VOA-1932A/1024/40 1919
    patches/Stroma/POLE/VOA-1932A/1024/40 131

    Time: 1167.56s

    TODO: check patch sizes
    """
    slide_path = mock_data['POLE/VOA-1932A']['slide_path']
    slide_coords_location = os.path.join(MOCK_DIR, 'slide_coords.json')
    patch_size = 1024
    args_str = f"""
    from-arguments
    --patch_location {OUTPUT_PATCH_DIR}
    use-directory
    --slide_location {SLIDE_DIR}
    use-slide-coords
    --slide_coords_location {slide_coords_location}
    """
    parser = extract_annotated_patches.parser.create_parser()
    config = parser.get_args(args_str.split())
    ape = AnnotatedPatchesExtractor(config)
    args = ape.produce_args([slide_path])
    slide_path, class_size_to_patch_path = args[0]
    ape.extract_patch_by_slide_coords(slide_path, class_size_to_patch_path)

    """Setup test data"""
    scm = SlideCoordsMetadata.load(slide_coords_location)
    cm = scm.get_slide('VOA-1932A')
    annotation = mock_data['POLE/VOA-1932A']['annotation']

    area = annotation.get_area()
    """Check Tumor patches"""
    extracted_coord_seq = list(cm.get_topleft_coords('Tumor'))
    patch_files = os.listdir(class_size_to_patch_path['Tumor'][patch_size])
    assert len(patch_files) > 0
    num_tumor_patch_files = len(patch_files)
    assert num_tumor_patch_files <= 200
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

        patch_file = os.path.join(class_size_to_patch_path['Tumor'][patch_size], patch_file)
        patch = Image.open(patch_file)
        assert patch.size == (patch_size, patch_size,)

    """Check Stroma patches"""
    extracted_coord_seq = list(cm.get_topleft_coords('Stroma'))
    patch_files = os.listdir(class_size_to_patch_path['Stroma'][patch_size])
    assert len(patch_files) > 0
    num_stroma_patch_files = len(patch_files)
    assert num_stroma_patch_files <= 200
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

        patch_file = os.path.join(class_size_to_patch_path['Stroma'][patch_size], patch_file)
        patch = Image.open(patch_file)
        assert patch.size == (patch_size, patch_size,)
    
    assert num_tumor_patch_files + num_stroma_patch_files == 200
