import os
import logging
import json
import psutil
from tqdm import tqdm
import numpy as np
import multiprocessing as mp
from openslide import OpenSlide

import submodule_utils as utils
from submodule_utils.subtype_enum import BinaryEnum
from submodule_utils.mixins import (OutputMixin, SlideCoordsMixin)
from submodule_utils.annotation import GroovyAnnotation
from submodule_utils.manifest.slide_coords import (
        SlideCoordsMetadata, CoordsMetadata)
import submodule_utils.image.preprocess as preprocess
# from submodule_utils.manifest.patient_slides import PatientSlidesMetadata
from submodule_cv.dataset import SlideCoordsExtractor

logger = logging.getLogger('extract_annotated_patches')

default_seed = 256
default_component_id = "extract_annotated_patches"

class AnnotatedPatchesExtractor(OutputMixin, SlideCoordsMixin):
    """Extracted annotated patches

    Attributes
    ----------
    slide_coords : SlideCoordsMetadata
        Metadata object containing slide coords to use in extracting patches.
        When 'use-annotation' is set, we DO NOT set slide_coords. Instead each child process creates a SlideCoordsMetadata and then uses multiprocess.Pipe to send them to the parent process to merge.
    """
    FULL_MAGNIFICATION = 40
    MAX_N_PROCESS = 10

    def get_magnification(self, resize_size):
        return int(float(resize_size) * float(self.FULL_MAGNIFICATION) \
            / float(self.patch_size))

    @property
    def should_use_manifest(self):
        return self.load_method == 'use-manifest'
    
    @property
    def should_use_directory(self):
        return self.load_method == 'use-directory'
    
    @property
    def should_use_slide_coords(self):
        return self.extract_method == 'use-slide-coords'

    @property
    def should_use_annotation(self):
        return self.subcommand == 'use-annotation'

    def get_slide_paths(self):
        """
        """
        if self.should_use_manifest:
            # return self.patient_slides.slidepaths
            raise NotImplementedError("use-manifest is not yet implemented")
        elif self.should_use_directory:
            return utils.get_paths(self.slide_location, self.slide_pattern,
                    extensions=['tiff', 'svs', 'scn'])
        else:
            raise NotImplementedError()

    def load_slide_annotation_lookup(self):
        """Load annotation TXT files from annotation_location and set up 

        Returns
        -------
        dict of str: GroovyAnnotation
            Lookup table for slide region annotations from slide names. 
        """
        slide_annotation = { }
        for file in os.listdir(self.annotation_location):
            slide_name = utils.path_to_filename(file)
            filepath = os.path.join(self.annotation_location, file)
            slide_annotation[slide_name] = GroovyAnnotation(filepath)
        return slide_annotation

    def __init__(self, config):
        """
        TODO: fix import-annotations and export-annotations
        """
        self.is_tumor = config.is_tumor
        self.seed = config.seed
        self.load_method = config.load_method
        if self.should_use_manifest:
            # self.manifest_location = config.manifest_location
            # self.patient_slides = .load(self.manifest_location)
            raise NotImplementedError("use-manifest is not yet implemented")
        elif self.should_use_directory:
            self.slide_location = config.slide_location
            self.slide_pattern = config.slide_pattern
        else:
            raise NotImplementedError(f"Load method {self.load_method} not implemented")
        
        self.extract_method = config.extract_method
        self.slide_coords_location = config.slide_coords_location
        if self.should_use_annotation:
            self.annotation_location = config.annotation_location
            self.slide_annotation = self.load_slide_annotation_lookup()
            self.patch_size = config.patch_size
            self.resize_sizes = config.resize_sizes
            self.__resize_sizes = config.resize_sizes
            self.max_slide_patches = config.max_slide_patches
        elif self.should_use_slide_coords:
            self.slide_coords_metadata = SlideCoordsMetadata.load(self.slide_coords_location)
            self.patch_size = self.slide_coords_metadata.patch_size
            self.resize_sizes = self.slide_coords_metadata.resize_sizes
        else:
            raise NotImplementedError(f"Extract method {self.extract_method} not implemented")

        if not self.resize_sizes:
            self.resize_sizes = [self.patch_size]
        
        self.slide_paths = self.get_slide_paths()
        self.n_process = psutil.cpu_count()
    
    def print_parameters(self):
        pass

    def extract_patch_by_slide_coords(self, slide_path, class_size_to_patch_path):
        slide_name = utils.path_to_filename(slide_path)
        os_slide = OpenSlide(slide_path)
        for data in self.slide_coords_metadata.get_slide(slide_name):
            label, coord = data
            x, y = coord
            if self.is_tumor and label != BinaryEnum(1).name:
                """Skip non-tumor patch if is_tumor is set.
                """
                continue

            patch = preprocess.extract(os_slide, x, y, self.patch_size)
            for resize_size in self.resize_sizes:
                patch_path = class_size_to_patch_path[label][resize_size]
                if resize_size == self.patch_size:
                    patch.save(os.path.join(patch_path, f"{x}_{y}.png"))
                else:
                    resized_patch = preprocess.resize(patch, resize_size)
                    resized_patch.save(os.path.join(patch_path, f"{x}_{y}.png"))


    def extract_patch_by_annotation(self, slide_path,
            class_size_to_patch_path, send_end):
        """Extracts patches using the steps:
         1. Moves a sliding, non-overlaping window to extract each patch to Pillow patch.
         2. Converts patch to ndarray ndpatch and skips to next patch if background

        Parameters
        ----------
        slide_path : str
            Path of slide to extract patch

        class_size_to_patch_path : dict
            To get the patch path a store evaluated patch using evaluated label name and patch size as keys

        send_end : multiprocessing.connection.Connection
            Connection to send recorded coords metadata of a slide to parent.
        """
        slide_name = utils.path_to_filename(slide_path)
        os_slide = OpenSlide(slide_path)
        coords = CoordsMetadata(slide_name, patch_size=self.patch_size)
        for idx, data in enumerate(SlideCoordsExtractor(os_slide, self.patch_size,
                shuffle=True, seed=self.seed)):
            if self.max_slide_patches and idx > self.max_slide_patches:
                """Stop extracting patches once we have reach the max number of them for this slide.
                """
                break
            patch, tile_loc, resized_patches = data
            tile_x, tile_y, x, y = tile_loc
            label = self.slide_annotation[slide_name].points_to_label(
                    np.array([[x, y],
                        [x+self.patch_size, y],
                        [x, y+self.patch_size],
                        [x+self.patch_size, y+self.patch_size]]))
            if not label:
                """Skip unlabeled patches
                """
                continue
            if self.is_tumor and label != BinaryEnum(1).name:
                """Skip non-tumor patch if is_tumor is set.
                """
                continue
            
            ndpatch = utils.image.preprocess.pillow_image_to_ndarray(
                    resized_patches[self.patch_size])
            if utils.image.preprocess.check_luminance(ndpatch):
                """Save labeled forground patch
                """
                for resize_size in self.resize_sizes:
                    patch_path = class_size_to_patch_path[label][resize_size]
                    resized_patches[resize_size].save(os.path.join(patch_path,
                            f"{x}_{y}.png"))
                coords.add_coord(label, x, y)
        send_end.send(coords)

    def produce_args(self, cur_slide_paths):
        """Produce arguments to send to patch extraction subprocess. Creates subdirectories for patches if necessary.

        Parameters
        ----------
        cur_slide_paths : list of str
            List of slide paths. Each path is sent to a subprocess to get slide to extract.
        
        Returns
        -------
        list of tuple
            List of argument tuples to pass through each process. Each argument tuple contains:
             - slide_path (str) path of slide to extract patch.
             - class_size_to_patch_path (dict of str: dict) to get the patch path a store resized patch using annotated label name and patch size as keys
        """
        args = []
        for slide_path in cur_slide_paths:
            slide_name = utils.path_to_filename(slide_path)
            slide_id = utils.create_patch_id(slide_path, self.slide_pattern)

            def make_patch_path(class_name):
                """Create patch path and cache it by size in resize_sizes using slide_id from method body.
                """
                size_patch_path = { }
                for resize_size in self.resize_sizes:
                    size_patch_path[resize_size] = os.path.join(
                            self.patch_location, class_name, slide_id,
                            str(resize_size), str(self.get_magnification(resize_size)))
                    os.makedirs(size_patch_path[resize_size], exist_ok=True)
                return size_patch_path

            class_size_to_patch_path = { }
            if self.should_use_annotation:
                if slide_name not in self.slide_annotation:
                    """Skip slide as there are no annotations for it.
                    """
                    continue
                if self.is_tumor:
                    tumor_label = BinaryEnum(1).name
                    if tumor_label in self.slide_annotation[slide_name].labels:
                        class_size_to_patch_path[tumor_label] = make_patch_path(tumor_label)
                else:
                    for label in self.slide_annotation[slide_name].labels:
                        class_size_to_patch_path[label] = make_patch_path(label)
            elif self.should_use_slide_coords:
                if not self.slide_coords_metadata.has_slide(slide_name):
                    """Skip slide as there are no slide coordinates for it.
                    """
                    continue
                if self.is_tumor:
                    tumor_label = BinaryEnum(1).name
                    if tumor_label in self.slide_coords_metadata \
                            .get_slide(slide_name).labels:
                        class_size_to_patch_path[tumor_label] \
                                = make_patch_path(tumor_label)
                else:
                    for label in self.slide_coords_metadata \
                            .get_slide(slide_name).labels:
                        class_size_to_patch_path[label] = make_patch_path(label)
            else:
                raise NotImplementedError(f"Extract method {self.extract_method} not implemented")
            arg = (slide_path, class_size_to_patch_path)
            args.append(arg)
        return args

    def run(self):
        """Run extract annotated patches.
        """
        self.print_parameters()
        if self.n_process > self.MAX_N_PROCESS:
            logger.info(f"Number of CPU processes of {self.n_process} is too high. Setting to {self.MAX_N_PROCESS}")
            self.n_process = self.MAX_N_PROCESS
        logger.info(f"Number of CPU processes: {self.n_process}")
        n_slides = len(self.slide_paths)
        coords_to_merge = []
        prefix = "Extracting from slides: "
        for idx in tqdm(range(0, n_slides, self.n_process),
                desc=prefix, dynamic_ncols=True):
            cur_slide_paths = self.slide_paths[idx:idx + self.n_process]
            processes = []
            recv_end_list = []
            for args in self.produce_args(cur_slide_paths):
                if self.should_use_annotation:
                    recv_end, send_end = mp.Pipe(False)
                    recv_end_list.append(recv_end)
                    args = (*args, send_end,)
                    p = mp.Process(target=self.extract_patch_by_annotation, args=args)
                elif self.should_use_slide_coords:
                    p = mp.Process(target=self.extract_patch_by_slide_coords, args=args)
                p.start()
                processes.append(p)
            for p in processes:
                p.join()
            coords_to_merge.extend(map(lambda x: x.recv(), recv_end_list))

        if self.should_use_annotation:
            """Merge slide coords
            """
            logger.info("Done loop. Saving slide coordinate metadata.")
            slide_coords = SlideCoordsMetadata(self.slide_coords_location,
                    patch_size=self.patch_size, resize_sizes=self.__resize_sizes)
            slide_coords.consume_coords(coords_to_merge)
            slide_coords.save()
        logger.info("Done.")