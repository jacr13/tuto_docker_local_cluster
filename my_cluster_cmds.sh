#!/usr/bin/env bash

#=========================================================
#Terminal Color Codes
#=========================================================
DEFAULT='\[\033[0m\]'
WHITE='\[\033[1;37m\]'
BLACK='\[\033[0;30m\]'
BLUE='\[\033[0;34m\]'
LIGHT_BLUE='\[\033[1;34m\]'
GREEN='\[\033[0;32m\]'
LIGHT_GREEN='\[\033[1;32m\]'
CYAN='\[\033[0;36m\]'
LIGHT_CYAN='\[\033[1;36m\]'
RED='\[\033[0;31m\]'
LIGHT_RED='\[\033[1;31m\]'
PURPLE='\[\033[0;35m\]'
LIGHT_PURPLE='\[\033[1;35m\]' #pink
Orange='\[\033[0;33m\]' #brown? - yellow
YELLOW='\[\033[1;33m\]' # light yellow
GRAY='\[\033[1;30m\]'
LIGHT_GRAY='\[\033[0;37m\]'

parse_git_branch() {
     git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}

#change text before cmd
PS1="($LIGHT_CYAN${CLUSTER}$DEFAULT)-$LIGHT_GREEN\u@\h$DEFAULT:$LIGHT_BLUE\w $RED\$(parse_git_branch)$DEFAULT$ "


alias my_report_cpu='sreport user top'
alias my_report_percent='sreport user topusage start=2/16/22 end=2/23/24 -t percent'

alias my_squeue='squeue --format="%.10i %.20P %.50j %.10u %.2t %.10M %.4D %R" -u $USER --sort="t,-S" -u $USER'

alias _squeue_helper='squeue -h --format="%.8i %30P %75j %.13u %.11L %.11l %.22S %.2t %.5D %.5C  %15R " --sort="t,-S" -u $USER'


function my_squeue_gpu() {
   my_squeue | grep gpu
}

function ask_permission () {
    echo "If you continue you will cancel $n_jobs/$n_total jobs..."
    read -p "Do you still want to continue? [y/n]? " -r
}

function my_scancel_pattern() {
    dryrun=1
    if [ $# -eq 0 ]
    then
        echo "No arguments supplied... Try -h or --help to get help."
        return
    fi
    while test $# -gt 0; do
        case "$1" in
            -h | --help)
                echo "Usage: my_scancel [option...]" >&2
                echo "   -h, --help             Show this help message"
                echo "   -p, --pattern [text]   pattern to match on grep"
                echo "   -nd, --no_dryrun       Doesn't show jobs in dry run mode (dangerous)"
                echo ""
                echo "This function will cancel all the jobs of USER that match pattern"
                return
                ;;
            -p | --pattern)
                shift
                pattern=$1
                shift
                ;;
            -nd | --no_dryrun)
                dryrun=0
                shift
                ;;
            *)
            echo "$1 is not a recognized flag!"
            return 1;
            ;;
        esac
    done
    n_jobs=$(_squeue_helper | grep -E -wc "$pattern")
    n_total=$(_squeue_helper | grep -E -c "$USER" )
    # jscpd:ignore-start
    if [ $dryrun -eq 1 ]
    then
        echo "[DRYRUN] Number of jobs before cancel: $n_total"
        echo "[DRYRUN] The following jobs are the ones that will be canceled!!"
        _squeue_helper | grep -E "$pattern"
        n_total=$(_squeue_helper | grep -E -c "$USER")
        echo "[DRYRUN] Number of jobs after cancel: $((n_total - n_jobs))"
    fi
    
    ask_permission
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo "Number of jobs before cancel: $n_total"
        _squeue_helper | grep -E "$pattern" |  awk '{print $1}' | xargs scancel
        echo "Waiting a bit for jobs to cancel..."
        sleep 5
        n_total=$(_squeue_helper | grep -E -c "$USER" )
        echo "Number of jobs after cancel: $n_total"
    fi
    # jscpd:ignore-end
}

function my_scancel_invert() {
    dryrun=1
    if [ $# -eq 0 ]
    then
        echo "No arguments supplied... Try -h or --help to get help."
        return
    fi
    while test $# -gt 0; do
        case "$1" in
            -h | --help)
                echo "Usage: my_scancel_invert [option...]" >&2
                echo "   -h, --help             Show this help message"
                echo "   -p, --pattern [text]   pattern to match on grep"
                echo "   -nd, --no_dryrun       Doesn't show jobs in dry run mode (dangerous)"
                echo ""
                echo "This function will cancel all the jobs of USER that DO NOT match pattern"
                return
                ;;
            -p | --pattern)
                shift
                pattern=$1
                shift
                ;;
            -nd | --no_dryrun)
                dryrun=0
                shift
                ;;
            *)
            echo "$1 is not a recognized flag!"
            return 1;
            ;;
        esac
    done
    n_jobs=$(_squeue_helper | grep -E -v -c "$pattern")
    n_total=$(_squeue_helper | grep -E -c "$USER" )
    # jscpd:ignore-start
    if [ $dryrun -eq 1 ]
    then
        echo "[DRYRUN] Number of jobs before cancel: $n_total"
        echo "[DRYRUN] The following jobs are the ones that will REMAIN all the other jobs will be canceled!!"
        _squeue_helper | grep -E "$pattern"
        n_total=$(_squeue_helper | grep -E -c "$USER")
        echo "[DRYRUN] Number of jobs after cancel: $((n_total - n_jobs))"
    fi
    
    ask_permission
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo "Number of jobs before cancel: $n_total"
        _squeue_helper | grep -E -v "$pattern" |  awk '{print $1}' | xargs scancel
        echo "Waiting a bit for jobs to cancel..."
        sleep 5
        n_total=$(_squeue_helper | grep -E -c "$USER" )
        echo "Number of jobs after cancel: $n_total"
    fi
    # jscpd:ignore-end
}

function my_scancel() {
    dryrun=1
    invert=0
    if [ $# -eq 0 ]
    then
        echo "No arguments supplied, this command will cancel ALL your jobs!"
        n_total=$(_squeue_helper | grep -E -c "$USER" )
        n_jobs="$n_total"
        ask_permission
        if [[ $REPLY =~ ^[Yy]$ ]]
        then
            scancel -u $USER
        fi
        return
    fi
    while test $# -gt 0; do
        case "$1" in
            -h | --help)
                echo "Usage: my_scancel_invert [option...]" >&2
                echo "   -h, --help             Show this help message"
                echo "   -p, --pattern [text]   pattern to match on grep (will cancel all jobs that match this pattern)"
                echo "   -i, --invert           invert the pattern, so now this command will KEEP jobs that match the pattern"
                echo "   -nd, --no_dryrun       Doesn't show jobs in dry run mode (dangerous)"
                echo ""
                echo "This command will cancel all the jobs of USER that match pattern if neither -i or --invert are specified, and cancel all jobs that DO NOT match the pattern if -i or --invert are specified!"
                return
                ;;
            -p | --pattern)
                shift
                pattern=$1
                shift
                ;;
            -i | --invert)
                invert=1
                shift
                ;;
            -nd | --no_dryrun)
                dryrun=0
                shift
                ;;
            *)
            echo "$1 is not a recognized flag!"
            return 1;
            ;;
        esac
    done

    dryrun_params=""
    if [ $dryrun -eq 0 ]
    then
        dryrun_params="--no_dryrun"
    fi

    if [ $invert -eq 1 ]
    then
        my_scancel_invert -p $pattern $dryrun_params
    else
        my_scancel_pattern -p $pattern $dryrun_params
    fi
}