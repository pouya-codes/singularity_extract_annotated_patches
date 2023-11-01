import argparse

from submodule_utils import (BALANCE_PATCHES_OPTIONS, DATASET_ORIGINS,
        PATCH_PATTERN_WORDS)
from submodule_utils.manifest.arguments import manifest_arguments
from submodule_utils.arguments import (
        AIMArgumentParser,
        dir_path, file_path, dataset_origin, balance_patches_options,
        str_kv, int_kv, subtype_kv, make_dict,
        ParseKVToDictAction, CustomHelpFormatter)
from extract_annotated_patches import *

description="""Extract annotated patches.
"""

epilog="""
"""

default_component_id = "extract_annotated_patches"

@manifest_arguments(description=description, epilog=epilog, default_component_id=default_component_id)
def create_parser(parser):
    parser_grp = parser.add_argument_group("required arguments")
    parser_grp.add_argument("--patch_location", type=dir_path, required=True,
            help="Directory path to extract patches to.")
    parser.add_argument("--is_tumor", action='store_true',
            help="Only extract tumor patches. Default extracts tumor and normal patches.")
    parser.add_argument("--seed", type=int, default=default_seed,
            help="Seed for random shuffle.")

    help_subparsers_load = """Specify how to load slides to extract.
    There are 2 ways of extracting slides: by manifest and by directory."""
    subparsers_load = parser.add_subparsers(dest='load_method',
            required=True,
            parser_class=AIMArgumentParser,
            help=help_subparsers_load)

    help_manifest = """Use manifest file to locate slides.
    A manifest JSON file contains keys 'patients', and optionally 'patient_regex' which is the regex string used to extract the patient from the slide name.
    The key 'patients' which is a dictionary where each key is a patient ID and value is a list of slide paths for the slides corresponding to the patient.

    {
        patient_regex: str|None,
        patients: {
            [patient ID]: [str, ...],
            ...
        }
    }"""
    parser_manifest = subparsers_load.add_parser("use-manifest",
            help=help_manifest)
    parser_manifest_grp = parser_manifest.add_argument_group("required arguments")
    parser_manifest_grp.add_argument("--manifest_location", type=file_path, required=True,
            help="Path to manifest JSON file")

    help_directory = """Use a rootdir to locate slides.
    It is expected that slide paths have the structure '/path/to/rootdir/slide_pattern/slide_name.extension' where slide_pattern is usually 'subtype'. Patient IDs are extrapolated from slide_name using known, hardcoded regex."""
    parser_directory = subparsers_load.add_parser("use-directory",
            help=help_directory)
    parser_directory_grp = parser_directory.add_argument_group("required arguments")
    parser_directory_grp.add_argument("--slide_location", type=dir_path, required=True,
            help="Path to slide rootdir.")
    parser_directory.add_argument("--slide_pattern", type=str,
            default='subtype',
            help="'/' separated words describing the directory structure of the "
            "slide paths. Normally slides paths look like "
            "/path/to/slide/rootdir/subtype/slide.svs and if slide paths are "
            "/path/to/slide/rootdir/slide.svs then simply pass ''.")

    subparsers_load_list = [parser_manifest, parser_directory]

    for subparser in subparsers_load_list:
        help_subparsers_extract = """Specify which coordinates in the slides to extract.
        There are 2 ways of extracting patches: by slide_cords and by annotation."""
        subparsers_extract = subparser.add_subparsers(dest="extract_method",
                required=True,
                parser_class=AIMArgumentParser,
                help=help_subparsers_extract)

        help_coords = """Specify patches to extract using slide coordinates.
        A slide coords JSON file containing keys 'patch_size' and 'coords'.
        The key 'patch_size' gives the pixel width, height of the patch.
        Coordinates are a list of size 2 lists of numbers representing the x, y pixel coordinates.
        The [x, y] list represents the coordinates of the top left corner of the patch_size * patch_size extracted patch.
        Coordinates are indexed by slide name for the slide the patches are from, and annotation the patches are labeled with.

        {
            patch_size: int,
            coords: {
                [slide name]: {
                    [label]: [
                        [int|float, int|float],
                        ...
                    ],
                    ...
                },
                ...
            }
        }"""
        parser_coords = subparsers_extract.add_parser("use-slide-coords",
                help=help_coords)
        parser_coords_grp = parser_coords.add_argument_group("required arguments")
        parser_coords_grp.add_argument("--slide_coords_location", type=file_path, required=True,
                help="Path to slide coords JSON file.")

        help_annotation = """Specify patches to extract by annotation.
        If a slide is named 'VOA-1823A' then the annotation file for that slide is a text file named 'VOA-1823A.txt' with each line containing (i.e.):

        Tumor [Point: 84332.8046875, 68421.28125, Point: 84332.8046875, 68421.28125,...]
        Stroma [...]"""
        parser_annotation = subparsers_extract.add_parser("use-annotation",
                help=help_annotation)
        parser_annotation_grp = parser_annotation.add_argument_group("required arguments")
        parser_annotation_grp.add_argument("--annotation_location", type=dir_path, required=True,
                help="Path to immediate directory containing slide's annotation TXTs.")
        parser_annotation_grp.add_argument("--slide_coords_location", type=str, required=True,
                help="Path to slide coords JSON file to save extracted patch coordinates.")
        parser_annotation.add_argument("--patch_size", type=int,
                default=default_patch_size,
                help="Patch size in pixels to extract from slide.")
        parser_annotation.add_argument("--resize_sizes", nargs='+', type=int, required=False,
                help="List of patch sizes in pixels to resize the extracted patches and save. "
                "Each size should be at most patch_size. "
                "Default simply saves the extracted patch.")
        parser_annotation.add_argument("--max_slide_patches", type=int, required=False,
                help="Select at most max_slide_patches number of patches from each slide.")
