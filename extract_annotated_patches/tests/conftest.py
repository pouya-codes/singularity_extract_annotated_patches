import os
import shutil
import pytest

from submodule_utils.metadata.annotation import GroovyAnnotation
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
        if os.path.isdir(OUTPUT_PATCH_DIR):
            shutil.rmtree(OUTPUT_PATCH_DIR)
        for file in os.listdir(OUTPUT_DIR):
            os.unlink(os.path.join(OUTPUT_DIR, file))

@pytest.fixture(scope='module')
def annotated_slide_names():
    return [utils.path_to_filename(file) for file in os.listdir(ANNOTATION_DIR)]

@pytest.fixture(scope='module')
def slide_paths():
    """Get path of all mock slides.
    """
    return utils.get_paths(SLIDE_DIR,
            utils.create_patch_pattern(default_slide_pattern),
            extensions=['tiff'])

@pytest.fixture(scope='module')
def mock_data(slide_paths):
    """Get path of slide with slide ID 'MMRd/VOA-1099A'. Fails when slide does not exist.
    """
    slide_ids = map(create_slide_id, slide_paths)
    slide_id_to_path = zip(slide_ids, slide_paths)
    payload = { }
    for id in ['MMRd/VOA-1099A', 'p53abn/VOA-3088B',
            'p53wt/VOA-3266C', 'POLE/VOA-1932A']:
        x = next(filter(lambda x: x[0] == id, slide_id_to_path))
        slide_id, slide_path = x
        _, slide_name = slide_id.split('/')
        annotation_path = os.path.join(ANNOTATION_DIR, f"{slide_name}.txt")
        payload[slide_id] = { }
        payload[slide_id]['slide_path'] = slide_path
        payload[slide_id]['annotation'] = GroovyAnnotation(annotation_path)
    return payload
