# -*- coding: utf-8 -*-

#   PyNAM -- Python Neural Associative Memory Simulator and Evaluator
#   Copyright (C) 2015 Andreas Stöckel
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Automatically include lib/pynnless if present
import os
import sys
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),
        "../lib/pynnless")))

# Import public classes/functions
from binam import BinaryMatrix, BiNAM
from data import generate, generate_naive, generate_random
from network import (InputParameters, OutputParameters, TopologyParameters,
        DataParameters, NetworkBuilder, NetworkPool)
from experiment import Experiment

# Current version of "PyNAM"
__version__ = "1.0.0"

# Export all explicitly imported classes/functions
__all__ = ['BinaryMatrix', 'BiNAM', 'NetworkBuilder', 'NetworkPool',
        'TopologyParameters', 'InputParameters', 'OutputParameters',
        'DataParameters', 'Experiment', 'generate', 'generate_naive',
        'generate_random']
