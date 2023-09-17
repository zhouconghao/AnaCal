#!/usr/bin/env bash

# This checks whether the script was executed or sourced
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
([[ -n $ZSH_EVAL_CONTEXT && $ZSH_EVAL_CONTEXT =~ :file$ ]] ||
[[ -n $KSH_VERSION && $(cd "$(dirname -- "$0")" &&
printf '%s' "${PWD%/}/")$(basename -- "$0") != "${.sh.file}" ]] ||
[[ -n $BASH_VERSION ]] && (return 0 2>/dev/null)) && sourced=1 || sourced=0

# This script should only be sourced
if [[ "${sourced}" == "0" ]]
then
    echo "You must source this script to use it, not execute it:"
    echo "source impt_config"
    exit
fi

retval=$?
if [ $retval -ne 0 ]
then
    return
fi

export JAX_ENABLE_X64="true"
export JAX_PLATFORMS="cpu"
export TF_CPP_MIN_LOG_LEVEL=10

export XLA_FLAGS="--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1"
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export XLA_PYTHON_CLIENT_PREALLOCATE="false"
export XLA_PYTHON_CLIENT_ALLOCATOR="platform"

echo "Your shell is now configured to run impt standard library"
