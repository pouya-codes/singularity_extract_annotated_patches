import os
import shutil
import pytest

from extract_annotated_patches import *
from extract_annotated_patches.tests import (
        OUTPUT_DIR, OUTPUT_PATCH_DIR, ANNOTATION_DIR,
        PATCH_PATTERN, PATCH_DIR, SLIDE_DIR,
        create_slide_id)

CLEAN_AFTER_RUN=False

@pytest.fixture
def clean_output():
    """Get the directory to save test outputs. Cleans the output directory before and after each test.
    """
    if os.path.isdir(OUTPUT_PATCH_DIR):
        shutil.rmtree(OUTPUT_PATCH_DIR)
    for file in os.listdir(OUTPUT_DIR):
        os.unlink(os.path.join(OUTPUT_DIR, file))
    os.mkdir(OUTPUT_PATCH_DIR)
    yield None
    if CLEAN_AFTER_RUN:
        if os.path.isdir(patch_dir):
            shutil.rmtree(patch_dir)
        for file in os.listdir(OUTPUT_DIR):
            os.unlink(os.path.join(OUTPUT_DIR, file))

@pytest.fixture(scope='module')
def annotated_slide_names():
    return [utils.path_to_filename(file) for file in os.listdir(ANNOTATION_DIR)]

@pytest.fixture(scope='module')
def slide_paths():
    return utils.get_paths(SLIDE_DIR,
            utils.create_patch_pattern(default_slide_pattern),
            extensions=['tiff'])

@pytest.fixture(scope='module')
def slide_path(slide_paths):
    """Get path of slide with slide ID 'MMRd/VOA-1099A'
    """
    slide_ids = map(create_slide_id, slide_paths)
    x = next(filter(lambda x: x[0] == 'MMRd/VOA-1099A', zip(slide_ids, slide_paths)))
    return x[1]
