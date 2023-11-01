import os
import shutil
import pytest
import numpy as np

from submodule_utils.metadata.annotation import GroovyAnnotation
from submodule_utils.metadata.slide_coords import (
        SlideCoordsMetadata, CoordsMetadata)

import extract_annotated_patches
from extract_annotated_patches import *
from extract_annotated_patches.tests import (
        OUTPUT_DIR, OUTPUT_PATCH_DIR, ANNOTATION_DIR,
        PATCH_PATTERN, PATCH_DIR, SLIDE_DIR,
        create_slide_id)

def test_mock(annotated_slide_names, slide_paths, slide_path):
    """Do a reality check with mock, ...etc variables.
    """
    assert default_patch_size == 1024
    assert len(annotated_slide_names) >= 4
    assert 'VOA-1099A' in annotated_slide_names
    assert 'VOA-3088B' in annotated_slide_names
    assert 'VOA-3266C' in annotated_slide_names
    assert 'VOA-1932A' in annotated_slide_names
    slide_ids = list(map(create_slide_id, slide_paths))
    assert len(slide_ids) >= 4
    assert 'MMRd/VOA-1099A' in slide_ids
    assert 'p53abn/VOA-3088B' in slide_ids
    assert 'p53wt/VOA-3266C' in slide_ids
    assert 'POLE/VOA-1932A' in slide_ids
    assert create_slide_id(slide_path) == 'MMRd/VOA-1099A'

def test_parse_args_1():
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
    assert config.is_tumor == False
    assert config.seed == default_seed
    assert config.load_method == 'use-directory'
    assert config.slide_location == SLIDE_DIR
    assert config.slide_pattern == default_slide_pattern
    assert config.extract_method == 'use-annotation'
    assert config.annotation_location == ANNOTATION_DIR
    assert config.patch_size == default_patch_size
    assert config.resize_sizes == []
    assert config.max_slide_patches == None
    ape = AnnotatedPatchesExtractor(config)
    assert not ape.should_use_manifest
    assert ape.should_use_directory
    assert ape.should_use_annotation
    assert not ape.should_use_slide_coords
    # TODO: finish asserts

def test_parse_args_2():
    pass

def test_get_slide_paths(slide_paths):
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
    assert sorted(slide_paths) == sorted(ape.get_slide_paths())
    
def test_load_slide_annotation_lookup(annotated_slide_names):
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
    slide_annotation = ape.load_slide_annotation_lookup()
    assert sorted(annotated_slide_names) == sorted(slide_annotation.keys())
    for slide_name, annotation in slide_annotation.items():
        assert isinstance(annotation, GroovyAnnotation)
        annotation_file = os.path.join(OUTPUT_DIR, f"{slide_name}.txt")
        ga = GroovyAnnotation(annotation_file)
        assert sorted(ga.labels) == sorted(annotation.labels)
        np.testing.assert_array_equal(ga.vertices, annotation.vertices)

def test_produce_args_1(clean_output, slide_path):
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
    assert len(args) == 1
    assert len(args[0]) == 2
    assert args[0][0] == slide_path
    slide_path, class_size_to_patch_path = args[0]
    assert sorted(['Stroma', 'Tumor']) == sorted(class_size_to_patch_path.keys())
    assert [default_patch_size] == list(class_size_to_patch_path['Stroma'].keys())
    assert [default_patch_size] == list(class_size_to_patch_path['Tumor'].keys())
    assert class_size_to_patch_path['Stroma'][default_patch_size] \
            == f"{OUTPUT_PATCH_DIR}/Stroma/MMRd/VOA-1099A/1024/40"
    assert class_size_to_patch_path['Tumor'][default_patch_size] \
            == f"{OUTPUT_PATCH_DIR}/Tumor/MMRd/VOA-1099A/1024/40"
    assert os.path.isdir(class_size_to_patch_path['Stroma'][default_patch_size])
    assert os.path.isdir(class_size_to_patch_path['Tumor'][default_patch_size])

class MockConnection(object):
    def __init__(self):
        self.obj = None

    def send(self, obj):
        self.obj = obj
    
    def recv(self, obj):
        return self.obj
