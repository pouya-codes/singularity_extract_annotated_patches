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

# @pytest.mark.skip(reason="")
def test_from_arguments_use_directory_annotation_1(clean_output, mock_data):
    """
    TODO: test SlideCoordsMetadata more
    Time: 1998.59s (0:33:18)
    """
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

    """Test SlideCoordsMetadata"""
    scm = SlideCoordsMetadata.load(slide_coords_location)

    for slide_id in mock_data.keys():
        _, slide_name = slide_id.split('/')
        annotation = mock_data[slide_id]['annotation']
        area = annotation.get_area()

        """Test Tumor patches"""
        extracted_coord_seq = list(scm.get_slide(slide_name).get_topleft_coords('Tumor'))
        patch_dir = f"{OUTPUT_PATCH_DIR}/Tumor/{slide_id}/1024/40"
        patch_files = os.listdir(patch_dir)
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

        """Test Stroma Patches"""
        extracted_coord_seq = list(scm.get_slide(slide_name).get_topleft_coords('Stroma'))
        patch_dir = f"{OUTPUT_PATCH_DIR}/Stroma/{slide_id}/1024/40"
        patch_files = os.listdir(patch_dir)
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

            patch_file = os.path.join(patch_dir, patch_file)
            patch = Image.open(patch_file)
            assert patch.size == (patch_size, patch_size,)

# @pytest.mark.skip(reason="")
def test_from_arguments_use_directory_annotation_2(clean_output, mock_data):
    """
    TODO: test SlideCoordsMetadata more
    Time: 1998.59s (0:33:18)
    """
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
    patch_size = 1024
    max_slide_patches = 200
    args_str = f"""
    from-arguments
    --patch_location {OUTPUT_PATCH_DIR}
    use-directory
    --slide_location {SLIDE_DIR}
    use-annotation
    --annotation_location {ANNOTATION_DIR}
    --slide_coords_location {slide_coords_location}
    --patch_size {patch_size}
    --max_slide_patches {max_slide_patches}
    """
    parser = extract_annotated_patches.parser.create_parser()
    config = parser.get_args(args_str.split())
    ape = AnnotatedPatchesExtractor(config)
    ape.run()

    """Test SlideCoordsMetadata"""
    scm = SlideCoordsMetadata.load(slide_coords_location)

    for slide_id in mock_data.keys():
        _, slide_name = slide_id.split('/')
        annotation = mock_data[slide_id]['annotation']
        area = annotation.get_area()

        """Test Tumor patches"""
        extracted_coord_seq = list(scm.get_slide(slide_name).get_topleft_coords('Tumor'))
        patch_dir = f"{OUTPUT_PATCH_DIR}/Tumor/{slide_id}/1024/40"
        patch_files = os.listdir(patch_dir)
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

        """Test Stroma Patches"""
        patch_dir = f"{OUTPUT_PATCH_DIR}/Stroma/{slide_id}/1024/40"
        patch_files = os.listdir(patch_dir)
        num_stroma_patch_files = len(patch_files)
        if num_stroma_patch_files > 0:
            extracted_coord_seq = list(scm.get_slide(slide_name).get_topleft_coords('Stroma'))
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

                patch_file = os.path.join(patch_dir, patch_file)
                patch = Image.open(patch_file)
                assert patch.size == (patch_size, patch_size,)

        assert num_tumor_patch_files + num_stroma_patch_files == 200


# @pytest.mark.skip(reason="not finished")
def test_from_arguments_use_directory_annotation_3(clean_output, mock_data):
    """
    TODO: test SlideCoordsMetadata more
    """
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
    patch_size = 1024
    resize_sizes = [512, 256]
    max_slide_patches = 200
    args_str = f"""
    from-arguments
    --patch_location {OUTPUT_PATCH_DIR}
    --is_tumor
    use-directory
    --slide_location {SLIDE_DIR}
    use-annotation
    --annotation_location {ANNOTATION_DIR}
    --slide_coords_location {slide_coords_location}
    --patch_size {patch_size}
    --resize_sizes {list_to_space_sep_str(resize_sizes)}
    --max_slide_patches {max_slide_patches}
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

        """Test Tumor patches"""
        extracted_coord_seq = list(scm.get_slide(slide_name).get_topleft_coords('Tumor'))
        patch_dir_512 = f"{OUTPUT_PATCH_DIR}/Tumor/{slide_id}/512/20"
        patch_dir_256 = f"{OUTPUT_PATCH_DIR}/Tumor/{slide_id}/256/10"
        patch_files_512 = os.listdir(patch_dir_512)
        patch_files_256 = os.listdir(patch_dir_256)
        assert len(patch_files_512) == max_slide_patches
        assert len(patch_files_512) == len(patch_files_256)
        assert len(patch_files_512) == len(extracted_coord_seq)

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

            patch_file_512 = os.path.join(patch_dir_512, patch_file_512)
            patch_file_256 = os.path.join(patch_dir_256, patch_file_256)
            patch_512 = Image.open(patch_file_512)
            patch_256 = Image.open(patch_file_256)
            assert patch_512.size == (512, 512,)
            assert patch_256.size == (256, 256,)
