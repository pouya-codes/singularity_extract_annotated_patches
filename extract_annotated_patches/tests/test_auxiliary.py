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

def test_mock(annotated_slide_names, slide_paths, mock_data):
    """Do a reality check with mock, ...etc variables.
    """
    #print(os.path.abspath(os.getcwd()))
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
    assert 'POLE/VOA-1932A' in mock_data

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
    assert config.resize_sizes == None
    assert config.max_slide_patches == None
    ape = AnnotatedPatchesExtractor(config)
    assert not ape.should_use_manifest
    assert ape.should_use_directory
    assert ape.should_use_annotation
    assert not ape.should_use_slide_coords
    assert ape.resize_sizes == [default_patch_size]
    assert ape.slide_pattern == utils.create_patch_pattern(default_slide_pattern)


def test_parse_args_2():
    patch_size = 2048
    resize_sizes = [512, 256]
    max_slide_patches = 100
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
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
    assert config.is_tumor == True
    assert config.seed == default_seed
    assert config.load_method == 'use-directory'
    assert config.slide_location == SLIDE_DIR
    assert config.slide_pattern == default_slide_pattern
    assert config.extract_method == 'use-annotation'
    assert config.annotation_location == ANNOTATION_DIR
    assert config.patch_size == patch_size
    assert config.resize_sizes == resize_sizes
    assert config.max_slide_patches == max_slide_patches
    ape = AnnotatedPatchesExtractor(config)
    assert not ape.should_use_manifest
    assert ape.should_use_directory
    assert ape.should_use_annotation
    assert not ape.should_use_slide_coords
    assert ape.patch_size == patch_size
    assert ape.resize_sizes == resize_sizes
    assert ape.slide_pattern == utils.create_patch_pattern(default_slide_pattern)
    assert ape.max_slide_patches == max_slide_patches


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
        annotation_file = os.path.join(ANNOTATION_DIR, f"{slide_name}.txt")
        ga = GroovyAnnotation(annotation_file)
        assert sorted(ga.labels) == sorted(annotation.labels)
        for label in ga.labels:
            expected_paths = ga.paths[label]
            actual_paths = annotation.paths[label]
            assert len(expected_paths) > 0
            assert len(expected_paths) == len(actual_paths)
            for expected_path, actual_path in zip(expected_paths, actual_paths):
                expected = expected_path.vertices
                actual = actual_path.vertices
                np.testing.assert_array_equal(expected, actual)


def test_produce_args_1(clean_output, mock_data):
    slide_path = mock_data['POLE/VOA-1932A']['slide_path']
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
            == f"{OUTPUT_PATCH_DIR}/Stroma/POLE/VOA-1932A/1024/40"
    assert class_size_to_patch_path['Tumor'][default_patch_size] \
            == f"{OUTPUT_PATCH_DIR}/Tumor/POLE/VOA-1932A/1024/40"
    assert os.path.isdir(class_size_to_patch_path['Stroma'][default_patch_size])
    assert os.path.isdir(class_size_to_patch_path['Tumor'][default_patch_size])


def test_produce_args_2(clean_output, mock_data):
    slide_path = mock_data['POLE/VOA-1932A']['slide_path']
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
    patch_size = 512
    resize_sizes = [256, 128]
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
    assert len(args) == 1
    assert len(args[0]) == 2
    assert args[0][0] == slide_path
    slide_path, class_size_to_patch_path = args[0]
    assert sorted(['Stroma', 'Tumor']) == sorted(class_size_to_patch_path.keys())
    assert sorted(resize_sizes) == sorted(class_size_to_patch_path['Stroma'].keys())
    assert sorted(resize_sizes) == sorted(class_size_to_patch_path['Tumor'].keys())
    assert class_size_to_patch_path['Stroma'][256] \
            == f"{OUTPUT_PATCH_DIR}/Stroma/POLE/VOA-1932A/256/20"
    assert class_size_to_patch_path['Stroma'][128] \
            == f"{OUTPUT_PATCH_DIR}/Stroma/POLE/VOA-1932A/128/10"

    assert class_size_to_patch_path['Tumor'][256] \
            == f"{OUTPUT_PATCH_DIR}/Tumor/POLE/VOA-1932A/256/20"
    assert class_size_to_patch_path['Tumor'][128] \
            == f"{OUTPUT_PATCH_DIR}/Tumor/POLE/VOA-1932A/128/10"

    assert os.path.isdir(class_size_to_patch_path['Stroma'][256])
    assert os.path.isdir(class_size_to_patch_path['Stroma'][128])
    assert os.path.isdir(class_size_to_patch_path['Tumor'][256])
    assert os.path.isdir(class_size_to_patch_path['Tumor'][128])


def test_produce_args_3(clean_output, mock_data):
    slide_path = mock_data['POLE/VOA-1932A']['slide_path']
    slide_coords_location = os.path.join(OUTPUT_DIR, 'slide_coords.json')
    patch_size = 512
    resize_sizes = [256, 128]
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
    """
    parser = extract_annotated_patches.parser.create_parser()
    config = parser.get_args(args_str.split())
    ape = AnnotatedPatchesExtractor(config)
    args = ape.produce_args([slide_path])
    assert len(args) == 1
    assert len(args[0]) == 2
    assert args[0][0] == slide_path
    slide_path, class_size_to_patch_path = args[0]
    assert ['Tumor'] == list(class_size_to_patch_path.keys())
    assert sorted(resize_sizes) == sorted(class_size_to_patch_path['Tumor'].keys())
    assert class_size_to_patch_path['Tumor'][256] \
            == f"{OUTPUT_PATCH_DIR}/Tumor/POLE/VOA-1932A/256/20"
    assert class_size_to_patch_path['Tumor'][128] \
            == f"{OUTPUT_PATCH_DIR}/Tumor/POLE/VOA-1932A/128/10"

    assert os.path.isdir(class_size_to_patch_path['Tumor'][256])
    assert os.path.isdir(class_size_to_patch_path['Tumor'][128])


def test_count_area():
    """Get a rough estimate of how many patches we can extract from mock slides.
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
    area = ape.slide_annotation['VOA-1099A'].get_area()
    print()
    print('MMRd/VOA-1099A')
    # VOA-1099A {'Stroma': 13.121841044401663, 'Tumor': 3748.764851032517} 3761.8866920769187
    print('Stroma: estimate patches extracted', area['Stroma'] / (1024**2))
    print('Tumor: estimate patches extracted', area['Tumor'] / (1024**2))
    area = ape.slide_annotation['VOA-3088B'].get_area()

    print('p53abn/VOA-3088B')
    # VOA-3088B {'Stroma': 166.66897720862426, 'Tumor': 3654.73569757063} 3821.404674779254
    print('Stroma: estimate patches extracted', area['Stroma'] / (1024**2))
    print('Tumor: estimate patches extracted', area['Tumor'] / (1024**2))
    area = ape.slide_annotation['VOA-1099A'].get_area()

    print('p53wt/VOA-3266C')
    # VOA-3266C {'Stroma': 54.97346750570068, 'Tumor': 1980.813060570782} 2035.7865280764827
    print('Stroma: estimate patches extracted', area['Stroma'] / (1024**2))
    print('Tumor: estimate patches extracted', area['Tumor'] / (1024**2))
    area = ape.slide_annotation['VOA-1932A'].get_area()

    print('POLE/VOA-1932A')
    # VOA-1932A {'Stroma': 178.88628345905454, 'Tumor': 2264.354263377558} 2443.2405468366123
    print('Stroma: estimate patches extracted', area['Stroma'] / (1024**2))
    print('Tumor: estimate patches extracted', area['Tumor'] / (1024**2))
