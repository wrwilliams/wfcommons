#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021-2023 The WfCommons Team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging
import os
import pathlib
import shutil

from abc import ABC, abstractmethod
from typing import Optional, Union

from ...common import FileLink, Task, Workflow
from ...wfinstances.instance import Instance


this_dir = pathlib.Path(__file__).resolve().parent

class Translator(ABC):
    """
    An abstract class of WfFormat parser for creating workflow benchmark applications.

    :param workflow: Workflow benchmark object or path to the workflow benchmark JSON instance.
    :type workflow: Union[Workflow, pathlib.Path]
    :param logger: The logger where to log information/warning or errors (optional).
    :type logger: logging.Logger
    """

    def __init__(self,
                 workflow: Union[Workflow, pathlib.Path],
                 logger: Optional[logging.Logger] = None) -> None:
        """Create an object of the translator."""
        self.logger = logging.getLogger(__name__) if logger is None else logger
        
        if isinstance(workflow, Workflow):
            self.workflow = workflow
        else:
            instance = Instance(workflow, logger=logger)
            self.workflow = instance.workflow

        self.workflow.write_json()

        # find all tasks
        self.tasks = {}
        for task in self.workflow.nodes.data():
            self.tasks[task[0]] = task[1]["task"]

        # find root, parents, and children tasks
        self.root_task_names = []
        self.task_parents = {}
        self.task_children = {}
        for task in self.workflow.workflow_json["workflow"]["tasks"]:
            if len(task["parents"]) == 0:
                if task["name"] not in self.root_task_names:
                    self.root_task_names.append(task["name"])
                    self.task_parents.setdefault(task['name'], [])
            else:
                for parent in task["parents"]:
                    self.task_parents.setdefault(task['name'], [])
                    self.task_parents[task['name']].append(parent)
            
            if len(task["children"]) == 0:
                self.task_children.setdefault(task['name'], [])
            else:
                for child in task["children"]:
                    self.task_children.setdefault(task['name'], [])
                    self.task_children[task['name']].append(child)

    @abstractmethod
    def translate(self, output_folder: pathlib.Path) -> None:
        """
        Translate a workflow benchmark description (WfFormat) into an actual workflow application.

        :param output_folder: The path to the folder in which the workflow benchmark will be generated.
        :type output_folder: pathlib.Path
        """

    def _copy_binary_files(self, output_folder: pathlib.Path) -> None:
        """
        Copy binary files to workflow benchmark's bin folder.

        :param output_folder: The path to the folder in which the workflow benchmark will be generated.
        :type output_folder: pathlib.Path
        """
        bin_folder = output_folder.joinpath("bin")
        bin_folder.mkdir()
        shutil.copy(this_dir.joinpath("../wfbench.py"), bin_folder)
        shutil.copy(shutil.which("cpu-benchmark"), bin_folder)

    def _generate_input_files(self, output_folder: pathlib.Path) -> None:
        """
        Generate workflow input files into workflow benchmark's data folder.

        :param output_folder: The path to the folder in which the workflow benchmark will be generated.
        :type output_folder: pathlib.Path
        """
        generated_files = []
        data_folder = output_folder.joinpath("data")
        data_folder.mkdir()
        for task_name in self.root_task_names:
            task = self.tasks[task_name]
            for file in task.files:
                if file.name not in generated_files and file.link == FileLink.INPUT:
                    generated_files.append(file.name)
                    with open(data_folder.joinpath(file.name), "wb") as fp:
                        fp.write(os.urandom(int(file.size)))

    def _write_output_file(self, contents: str, output_file_path: pathlib.Path) -> None:
        """
        Write the translated content to a file.

        :param contents: Contents to be written to the output file.
        :type contents: str
        :param output_file_path: The path of the output file.
        :type output_file_path: pathlib.Path
        """
        # file will be written to the same folder as for the original JSON instance.
        with open(output_file_path, "w") as out:
            out.write(contents)
        self.logger.info(f"Translated content written to '{output_file_path}'")

    def _find_children(self, task_name: str) -> list[Task]:
        """
        Find the children for a specific task.

        :param task_name: The task name.
        :type task_name: str

        :return: List of task's children.
        :rtype: List[Task]
        """
        self.logger.debug(f"Finding children for task '{task_name}'")
        children = []
        for node in self.instance.instance["workflow"]["tasks"]:
            if node["name"] == task_name:
                children = node["children"]

        return children

    def _find_parents(self, task_name: str) -> list[Task]:
        """
        Find the parents for a specific task.

        :param task_name: The task name.
        :type task_name: str

        :return: List of task's parents.
        :rtype: List[Task]
        """
        self.logger.debug(f"Finding parents for task '{task_name}'")
        parents = []
        for node in self.instance.instance["workflow"]["tasks"]:
            if node["name"] == task_name:
                parents = node["parents"]

        return parents
