# -*- coding: utf-8 -*-
"""
This file contains helper functions to work with SDPA.

Created on Fri May 16 13:52:58 2014

@author: Peter Wittek
"""
from bisect import bisect_left
from subprocess import call
import tempfile
import os
import numpy as np
from .nc_utils import convert_monomial_to_string

def parse_solution_matrix(iterator):
    solution_matrix = []
    while True:
        sol_mat = None
        in_matrix = False
        i = 0
        for row in iterator:
            if row.find('}') < 0:
                continue
            if row.startswith('}'):
                break
            if row.find('{') != row.rfind('{'):
                in_matrix = True
            numbers = row[row.rfind('{')+1:row.find('}')].strip().split(',')
            if sol_mat is None:
                sol_mat = np.empty((len(numbers), len(numbers)))
            for j, number in enumerate(numbers):
                sol_mat[i, j] = float(number)
            if row.find('}') != row.rfind('}') or not in_matrix:
                break
            i += 1
        solution_matrix.append(sol_mat)
        if row.startswith('}'):
            break
    return solution_matrix

def read_sdpa_out(filename, solutionmatrix=False):
    """Helper function to parse the output file of SDPA.

    :param filename: The name of the SDPA output file.
    :type filename: str.
    :param solutionmatrix: Optional parameter for retrieving the solution matrix.
    :type solutionmatrix: bool.
    :returns: tuple of two floats and optionally two lists of `numpy.array`
    """
    file_ = open(filename, 'r')
    for line in file_:
        if line.find("objValPrimal") > -1:
            primal = float((line.split())[2])
        if line.find("objValDual") > -1:
            dual = float((line.split())[2])
        if solutionmatrix:
            if line.find("xMat =") > -1:
                x_mat = parse_solution_matrix(file_)
            if line.find("yMat =") > -1:
                y_mat = parse_solution_matrix(file_)
    file_.close()
    if solutionmatrix:
        return primal, dual, x_mat, y_mat
    else:
        return primal, dual


def solve_with_sdpa(sdpRelaxation, solverparameters=None):
    """Helper function to write out the SDP problem to a temporary
    file, call the solver, and parse the output.

    :param sdpRelaxation: The SDP relaxation to be solved.
    :type sdpRelaxation: :class:`ncpol2sdpa.SdpRelaxation`.
    :param solutionmatrix: Optional parameter for retrieving the solution
                           matrix.
    :type solutionmatrix: bool.
    :param solverexecutable: Optional paramater to specify the name of the
                             executable if sdpa is not in the path or has a
                             different name.
    :type solverexecutable: str.
    :returns: tuple of float -- the primal and dual solution of the SDP,
              respectively.
    """
    solverexecutable = "sdpa"
    if solverparameters is not None and solverparameters.has_key("executable"):
        solverexecutable = solverparameters["executable"]
    primal, dual = 0, 0
    tempfile_ = tempfile.NamedTemporaryFile()
    tmp_filename = tempfile_.name
    tempfile_.close()
    tmp_dats_filename = tmp_filename + ".dat-s"
    tmp_out_filename = tmp_filename + ".out"
    write_to_sdpa(sdpRelaxation, tmp_dats_filename)
    if sdpRelaxation.verbose < 2:
        with open(os.devnull, "w") as fnull:
            call([solverexecutable, tmp_dats_filename, tmp_out_filename],
                 stdout=fnull, stderr=fnull)
    else:
        call([solverexecutable, tmp_dats_filename, tmp_out_filename])
    primal, dual, x_mat, y_mat = read_sdpa_out(tmp_out_filename, True)
    if sdpRelaxation.verbose < 2:
        os.remove(tmp_dats_filename)
        os.remove(tmp_out_filename)
    return primal, dual, x_mat, y_mat

def convert_row_to_sdpa_index(block_struct, row_offsets, row):
    """Helper function to map to sparse SDPA index values.
    """
    block_index = bisect_left(row_offsets[1:], row + 1)
    width = block_struct[block_index]
    row = row - row_offsets[block_index]
    i, j = divmod(row, width)
    return block_index, i, j


def write_to_sdpa(sdpRelaxation, filename):
    """Write the SDP relaxation to SDPA format.

    :param sdpRelaxation: The SDP relaxation to write.
    :type sdpRelaxation: :class:`ncpol2sdpa.SdpRelaxation`.
    :param filename: The name of the file. It must have the suffix ".dat-s"
    :type filename: str.
    """
    # Coefficient matrices
    row_offsets = [0]
    cumulative_sum = 0
    for block_size in sdpRelaxation.block_struct:
        cumulative_sum += block_size ** 2
        row_offsets.append(cumulative_sum)
    multiplier = 1
    if sdpRelaxation.F_struct.dtype == np.complex128:
        multiplier = 2
    lines = [[] for _ in range(multiplier*sdpRelaxation.n_vars+1)]
    for row in range(len(sdpRelaxation.F_struct.rows)):
        if len(sdpRelaxation.F_struct.rows[row]) > 0:
            col_index = 0
            for k in sdpRelaxation.F_struct.rows[row]:
                value = sdpRelaxation.F_struct.data[row][col_index]
                col_index += 1
                block_index, i, j = convert_row_to_sdpa_index(
                    sdpRelaxation.block_struct, row_offsets, row)
                if k == 0:
                    value *= -1
                if sdpRelaxation.F_struct.dtype == np.float64:
                    lines[k].append('{0}\t{1}\t{2}\t{3}\n'.format(
                        block_index + 1, i + 1, j + 1, value))
                else:
                    bs = sdpRelaxation.block_struct[block_index]
                    if value.real != 0:
                        lines[k].append('{0}\t{1}\t{2}\t{3}\n'.format(
                            block_index + 1, i + 1, j + 1, value.real))
                        lines[k].append('{0}\t{1}\t{2}\t{3}\n'.format(
                            block_index + 1, i + bs + 1, j + bs + 1, value.real))
                    if value.imag != 0:
                        lines[k + sdpRelaxation.n_vars].append('{0}\t{1}\t{2}\t{3}\n'.format(
                            block_index + 1, i + 1, j + bs + 1, value.imag))
                        lines[k + sdpRelaxation.n_vars].append('{0}\t{1}\t{2}\t{3}\n'.format(
                            block_index + 1, j + 1, i + bs + 1, -value.imag))
    file_ = open(filename, 'w')
    file_.write('"file ' + filename + ' generated by ncpol2sdpa"\n')
    file_.write(str(multiplier*sdpRelaxation.n_vars) + ' = number of vars\n')
    file_.write(str(len(sdpRelaxation.block_struct)) + ' = number of blocs\n')
    # bloc structure
    block_struct = [multiplier*blk_size for blk_size in sdpRelaxation.block_struct]
    file_.write(str(block_struct).replace('[', '(')
                .replace(']', ')'))
    file_.write(' = BlocStructure\n')
    # c vector (objective)
    objective = str(list(sdpRelaxation.obj_facvar)).replace(
                '[', '').replace(']', '')
    if multiplier == 2:
        objective += ', ' + objective
    file_.write('{'+objective+'}\n')
    for k, line in enumerate(lines):
        if line == []:
            continue
        for item in line:
            file_.write('{0}\t'.format(k)+item)
    file_.close()


def write_to_human_readable(sdpRelaxation, filename):
    """Write the SDP relaxation to a human-readable format.

    :param sdpRelaxation: The SDP relaxation to write.
    :type sdpRelaxation: :class:`ncpol2sdpa.SdpRelaxation`.
    :param filename: The name of the file.
    :type filename: str.
    """

    objective = ""
    indices_in_objective = []
    for i, tmp in enumerate(sdpRelaxation.obj_facvar):
        candidates = [key for key, v in
                      sdpRelaxation.monomial_index.iteritems() if v == i+1]
        if len(candidates) > 0:
            monomial = convert_monomial_to_string(candidates[0])
        else:
            monomial = ""
        if tmp > 0:
            objective += "+"+str(tmp)+monomial
            indices_in_objective.append(i)
        elif tmp < 0:
            objective += str(tmp)+monomial
            indices_in_objective.append(i)

    matrix_size = 0
    cumulative_sum = 0
    row_offsets = [0]
    block_offset = [0]
    for bs in sdpRelaxation.block_struct:
        matrix_size += abs(bs)
        cumulative_sum += bs ** 2
        row_offsets.append(cumulative_sum)
        block_offset.append(matrix_size)

    matrix = []
    for i in range(matrix_size):
        matrix_line = ["0"] * matrix_size
        matrix.append(matrix_line)

    for row in range(len(sdpRelaxation.F_struct.rows)):
        if len(sdpRelaxation.F_struct.rows[row]) > 0:
            col_index = 0
            for k in sdpRelaxation.F_struct.rows[row]:
                value = sdpRelaxation.F_struct.data[row][col_index]
                col_index += 1
                block_index, i, j = convert_row_to_sdpa_index(
                    sdpRelaxation.block_struct, row_offsets, row)
                candidates = [key for key, v in
                              sdpRelaxation.monomial_index.iteritems()
                              if v == k]
                if len(candidates) > 0:
                    monomial = convert_monomial_to_string(candidates[0])
                else:
                    monomial = ""
                offset = block_offset[block_index]
                if matrix[offset+i][offset+j] == "0":
                    matrix[offset+i][offset+j] = ("%s%s" % (value, monomial))
                else:
                    if value.real > 0:
                        matrix[offset+i][offset+j] += ("+%s%s" % (value, monomial))
                    else:
                        matrix[offset+i][offset+j] += ("%s%s" % (value, monomial))


    f = open(filename, 'w')
    f.write("Objective:" + objective + "\n")
    for matrix_line in matrix:
        f.write(str(list(matrix_line)).replace('[', '').replace(']', '')
                .replace('\'', ''))
        f.write('\n')
    f.close()
