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
        create_slide_id, list_to_space_sep_str)

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

        """Test Stroma Patches
        """
        extracted_coord_seq = scm.get_slide(slide_name).get_topleft_coords('Stroma')
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
