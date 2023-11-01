import argparse

from submodule_utils import (BALANCE_PATCHES_OPTIONS, DATASET_ORIGINS,
        PATCH_PATTERN_WORDS)
from submodule_utils.manifest.arguments import manifest_arguments
from submodule_utils.arguments import (
        AIMArgumentParser,
        dir_path, file_path, dataset_origin, balance_patches_options,
        str_kv, int_kv, subtype_kv, make_dict, positive_int, float_less_one,
        ParseKVToDictAction, CustomHelpFormatter)
from extract_annotated_patches import *

description="""Extract annotated patches.
"""

epilog="""
"""

@manifest_arguments(description=description, epilog=epilog,
        default_component_id=default_component_id)
def create_parser(parser):
    parser_grp = parser.add_argument_group("required arguments")
    parser_grp.add_argument("--hd5_location", type=dir_path, required=True,
            help="Path to root directory to save hd5 into.")
    parser.add_argument("--seed", type=int, default=default_seed,
            help="Seed for random shuffle.")
    parser.add_argument("--num_patch_workers", type=int,
            help="Number of worker processes to multi-process patch extraction. "
            "Default sets the number of worker processes to the number of CPU processes.")
    parser.add_argument("--store_thumbnail", action='store_true',
            help="Whether or not save thumbnail with showing the position "
            "of extracted patches. If yes, it will be stored at a folder called "
            "Thumbnails in HD5 folder.")

    help_subparsers_load = """Specify how to load slides to extract.
    There are 3 ways of extracting slides: from hd5 files, by manifest and by directory."""
    subparsers_load = parser.add_subparsers(dest='load_method',
            required=True,
            parser_class=AIMArgumentParser,
            help=help_subparsers_load)

    parser_hd5_files = subparsers_load.add_parser("from-hd5-files",
            help="uses pre created hd5 files located at hd5_location to create and store images in patch_location")
    parser_hd5_files.add_argument("--slide_location", type=dir_path, required=True,
            help="Path to slide rootdir.")
    parser_hd5_files.add_argument("--slide_pattern", type=str,
            default='subtype',
            help="'/' separated words describing the directory structure of the "
            "slide paths. Normally slides paths look like "
            "/path/to/slide/rootdir/subtype/slide.svs and if slide paths are "
            "/path/to/slide/rootdir/slide.svs then simply pass ''.")
    parser_hd5_files.add_argument("--slide_idx", type=positive_int,
            help="Positive Index for selecting part of slides instead of all of it. "
            "(useful for array jobs)")
    parser_hd5_files.add_argument("--resize", nargs='+', type=int,
            help="List for determining desired resize. For example, if the HDF5 file"
            " has [256, 512, 1024] patches, and we are only interested in 256, we "
            "set this flag. [256]")
    parser_hd5_files.add_argument("--max_num_patches", type=int,
            help="Maximum number of patches we want to extract. For example, if there are "
            "2000 patches from each HDF5, and we only need first 500 ones, we set this flag "
            "to 500. NOTE: The patches are same order that was supposed to be extracted.")


    help_manifest = """Use manifest file to locate slides.
        a CSV file with minimum of 4 column and maximum of 6 columns. The name of columns
        should be among ['origin', 'patient_id', 'slide_id', 'slide_path', 'annotation_path', 'subtype'].
        origin, slide_id, patient_id must be one of the columns."""
    parser_manifest = subparsers_load.add_parser("use-manifest",
            help=help_manifest)
    parser_manifest_grp = parser_manifest.add_argument_group("required arguments")
    parser_manifest_grp.add_argument("--patch_location", type=dir_path, required=True,
            help="Path to root directory to extract patches into.")
    parser_manifest_grp.add_argument("--manifest_location", type=file_path, required=True,
            help="Path to manifest CSV file.")
    parser_manifest.add_argument("--slide_idx", type=positive_int,
            help="Positive Index for selecting part of slides instead of all of it. "
            "(useful for array jobs)")
    parser_manifest.add_argument("--store_extracted_patches", action='store_true',
            help="Whether or not save extracted patches as png files on the disk.")

    help_directory = """Use a rootdir to locate slides.
    It is expected that slide paths have the structure '/path/to/rootdir/slide_pattern/slide_name.extension' where slide_pattern is usually 'subtype'. Patient IDs are extrapolated from slide_name using known, hardcoded regex."""
    parser_directory = subparsers_load.add_parser("use-directory",
            help=help_directory)
    parser_directory_grp = parser_directory.add_argument_group("required arguments")
    parser_directory_grp.add_argument("--patch_location", type=dir_path, required=True,
            help="Path to root directory to extract patches into.")
    parser_directory_grp.add_argument("--slide_location", type=dir_path, required=True,
            help="Path to slide rootdir.")
    parser_directory.add_argument("--store_extracted_patches", action='store_true',
            help="Whether or not save extracted patches as png files on the disk.")
    parser_directory.add_argument("--store_extracted_patches_as_hd5", action='store_true',
            help="Whether or not save extracted patches as hd5 files on the disk.")
    parser_directory.add_argument("--slide_idx", type=positive_int,
            help="Positive Index for selecting part of slides instead of all of it. "
            "(useful for array jobs)")
    parser_directory.add_argument("--slide_pattern", type=str,
            default='',
            help="'/' separated words describing the directory structure of the "
            "slide paths. Normally slides paths look like "
            "/path/to/slide/rootdir/subtype/slide.svs and if slide paths are "
            "/path/to/slide/rootdir/slide.svs then simply pass '' (using bash "
            "script, it is impossible to pass '', therefore in that case, use \"'\".).")
    parser_directory.add_argument("--mask_location", type=dir_path,
            help="Path to root directory which contains mask for tissue selection. "
            "It should contain png files or annotation file with label clear_area.")

    subparsers_load_list = [parser_manifest, parser_directory]

    for subparser in subparsers_load_list:
        help_subparsers_extract = """Specify which coordinates in the slides to extract.
        There are 3 ways of extracting patches: by slide_cords, by annotation, and by entire_slide."""
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
        if subparser == parser_manifest:
            parser_annotation.add_argument("--annotation_location", type=dir_path, required=False,
                    help="Path to immediate directory containing slide's annotation TXTs.")
        else:
            parser_annotation_grp.add_argument("--annotation_location", type=dir_path, required=True,
                    help="Path to immediate directory containing slide's annotation TXTs.")
        parser_annotation_grp.add_argument("--slide_coords_location", type=str, required=True,
                help="Path to slide coords JSON file to save extracted patch coordinates.")
        parser_annotation.add_argument("--patch_size", type=int,
                default=default_patch_size,
                help="Patch size in pixels to extract from slide.")
        parser_annotation.add_argument("--stride", type=int,
                default=0,
                help="Stride in pixels which determines the gap between each two extracted patches."
                " NOTE: This value will be added with the patch_size for actual stride."
                "For example, if patch_size is 2048 and stride is 2000, the actual stride "
                "is 2000+2048=4048.")
        parser_annotation.add_argument("--resize_sizes", nargs='+', type=int,
                help="List of patch sizes in pixels to resize the extracted patches and save. "
                "Each size should be at most patch_size. "
                "Default simply saves the extracted patch.")
        parser_annotation.add_argument("--is_tumor", action='store_true',
                    help="Only extract tumor patches. Default extracts tumor and normal patches.")
        parser_annotation.add_argument("--is_TMA", action='store_true',
                help="TMA cores are simple image instead of slide.")
        parser_annotation.add_argument("--patch_overlap", type=float,
                default=0, help="Overlap between extracted patches.")
        parser_annotation.add_argument("--annotation_overlap", type=float,
                default=1.0, help="Patches having overlapp above this value with the annotated pixels will be extracted.")
        parser_annotation.add_argument("--max_slide_patches", type=int,
                help="Select at most max_slide_patches number of patches from each slide.")

        help_entire = """Extracting patches from the whole slide. In this way,
        both tumor and normal areas will be extracted.
        The label is called Mix."""
        parser_entire = subparsers_extract.add_parser("use-entire-slide",
                help=help_entire)
        parser_entire_grp = parser_entire.add_argument_group("required arguments")
        parser_entire_grp.add_argument("--slide_coords_location", type=str, required=True,
                help="Path to slide coords JSON file to save extracted patch coordinates.")
        parser_entire.add_argument("--patch_size", type=int,
                default=default_patch_size,
                help="Patch size in pixels to extract from slide.")
        parser_entire.add_argument("--stride", type=int,
                default=0,
                help="Stride in pixels which determines the gap between each two extracted patches."
                " NOTE: This value will be added with the patch_size for actual stride."
                "For example, if patch_size is 2048 and stride is 2000, the actual stride "
                "is 2000+2048=4048.")
        parser_entire.add_argument("--resize_sizes", nargs='+', type=int,
                help="List of patch sizes in pixels to resize the extracted patches and save. "
                "Each size should be at most patch_size. "
                "Default simply saves the extracted patch.")
        parser_entire.add_argument("--max_slide_patches", type=int,
                help="Select at most max_slide_patches number of patches from each slide.")

        help_mosaic = """Selecting patches from the whole slide in an efficient way.
        In this way, first all patches will be clustered based on their RGB histogram.
        Then, in each cluster, another clustering will be applied for their coordiantes."""
        parser_mosaic = subparsers_extract.add_parser("use-mosaic",
                help=help_mosaic)
        parser_mosaic_grp = parser_mosaic.add_argument_group("required arguments")
        parser_mosaic_grp.add_argument("--slide_coords_location", type=str, required=True,
                help="Path to slide coords JSON file to save extracted patch coordinates.")
        parser_mosaic.add_argument("--patch_size", type=int,
                default=default_patch_size,
                help="Patch size in pixels to extract from slide.")
        parser_mosaic.add_argument("--evaluation_size", type=int,
                default=default_evaluation_size,
                help="Patch size in pixels to calculate clusters based on that. "
                "This should be at lower resolution (e.g. 5x) since it has more "
                "contexual information.")
        parser_mosaic.add_argument("--n_clusters", type=positive_int,
                default=9,
                help="Number of color clusters. This value should "
                "be selected based on the slide.")
        parser_mosaic.add_argument("--percentage", type=float_less_one,
                default=0.05,
                help="Percentage of patches to build the mosaic.")
        parser_mosaic.add_argument("--stride", type=int,
                default=0,
                help="Stride in pixels which determines the gap between each two extracted patches."
                " NOTE: This value will be added with the patch_size for actual stride."
                "For example, if patch_size is 2048 and stride is 2000, the actual stride "
                "is 2000+2048=4048.")
        parser_mosaic.add_argument("--resize_sizes", nargs='+', type=int,
                help="List of patch sizes in pixels to resize the extracted patches and save. "
                "Each size should be at most patch_size. "
                "Default simply saves the extracted patch.")

        # insert common things in here!
        subparsers_radius_list = [parser_annotation, parser_entire, parser_mosaic]

        for subparser in subparsers_radius_list:
            subparser.add_argument("--use_radius", action='store_true',
                help="Activating this subparser will enable extracting "
                "all patches within radius of the coordinate.")
            subparser.add_argument("--radius", type=int, default=1,
                help="From each selected coordinate, all its neighbours will be extracted. "
                "This number will be multiplied by the patch size."
                "Note: In use-annotation, the number will be multiplied*stride.")
