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

#=========================================================
# change PS1
#=========================================================

parse_git_branch() {
     git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}

human_num() {
    local n="$1"

    # Under 100k → show in k (1 decimal)
    if (( n < 100000 )); then
        printf "%.1fk" "$(echo "$n / 1000" | bc -l)"
        return
    fi

    # 100k or more → show in M (2 decimals)
    printf "%.2fM" "$(echo "$n / 1000000" | bc -l)"
}

usage_block() {
    local FILE="$HOME/.my_hpc_usage.env"

    # Default if file missing
    [[ ! -f "$FILE" ]] && echo "[-/-/-]" && return

    # Read the env file into associative array
    declare -A env
    while IFS='=' read -r key value; do
        [[ -z "$key" ]] && continue
        env[$key]="$value"
    done < "$FILE"

    # Shortcuts
    local my=${env[HPC_MY_USAGE]}
    local team=${env[HPC_TEAM_USAGE]}
    local total=${env[HPC_TEAM_BUDGET_YEAR]}
    local mypct=${env[HPC_MY_PCT]}
    local teampct=${env[HPC_TEAM_PCT]}
    local maxpct=${env[HPC_MAX_PCT]}

    # Safety defaults
    mypct=${mypct%.*}
    teampct=${teampct%.*}
    maxpct=${maxpct%.*}
    my=$(human_num "$my")
    team=$(human_num "$team")
    total=$(human_num "$total")


    # Print the block
    echo "[${my}/${team}/${total} | ${mypct}/${maxpct}/${teampct}%]"
}

#change text before cmd
PS1="($LIGHT_CYAN${CLUSTER}$DEFAULT)-[\$(usage_block)]-$LIGHT_GREEN\u@\h$DEFAULT:$LIGHT_BLUE\w $RED\$(parse_git_branch)$DEFAULT$ "

#=========================================================
#
#=========================================================

alias my_report_cpu='sreport user top'
alias my_report_percent='sreport user topusage start=2/16/22 end=2/23/24 -t percent'

alias my_squeue='squeue --format="%.10i %.20P %.50j %.10u %.2t %.10M %.4D %R" -u $USER --sort="t,-S" -u $USER'

alias _squeue_helper='squeue -h --format="%.8i %150j %.13u %.11M %.11L %.11l %.2t" --sort="t,-S" -u $USER'

alias mosh_kill='kill "pidof mosh-server"'

alias srj='squeue -u $USER -t RUNNING'


function update_my_cmds() {
    wget -q https://raw.githubusercontent.com/jacr13/tuto_docker_local_cluster/main/my_cluster_cmds.sh \
         -O "$HOME/my_cluster_cmds.sh"

    wget -q https://raw.githubusercontent.com/jacr13/tuto_docker_local_cluster/main/cluster_usage_scipts/my_usage_script.py \
         -O "$HOME/my_usage_script.py"

    source "$HOME/.bashrc"
}

# squeue running count
function src() {
    N_JOBS_TOTAL=$(_squeue_helper | grep -E -c "$USER" )
    N_JOBS_RUNNING=$(_squeue_helper | grep -wc R )
    echo "Jobs running: $N_JOBS_RUNNING/$N_JOBS_TOTAL"
}

function my_squeue_gpu() {
   my_squeue | grep gpu
}

function ask_permission () {
    n_jobs_to_cancel="$1"
    n_total="$2"
    echo "If you continue you will cancel $n_jobs_to_cancel/$n_total jobs..."
    read -p "Do you still want to continue? [y/n]? " -r
}

function convert_to_seconds() {
    local time=$1

    local days=0
    local hours=0
    local minutes=0
    local seconds=0

    # Check if the format includes days, hours, minutes, and seconds (d-hh:mm:ss)
    if [[ $time == *-*:*:* ]]; then
        # Extract time components with days
        local days=$(echo "$time" | cut -d'-' -f1)
        local hours=$(echo "$time" | awk -F ':' '{print $1}' | cut -d'-' -s -f2)
        local minutes=$(echo "$time" | awk -F ':' '{print $2}')
        local seconds=$(echo "$time" | awk -F ':' '{print $3}')
    # Check if the format includes hours, minutes, and seconds (hh:mm:ss)
    elif [[ $time == *:*:* ]]; then
        # Extract time components without days
        local hours=$(echo "$time" | awk -F ':' '{print $1}')
        local minutes=$(echo "$time" | awk -F ':' '{print $2}')
        local seconds=$(echo "$time" | awk -F ':' '{print $3}')
    # Check if the format includes minutes and seconds (mm:ss)
    elif [[ $time == *:* ]]; then
        # Extract time components without days and hours
        local minutes=$(echo "$time" | awk -F ':' '{print $1}')
        local seconds=$(echo "$time" | awk -F ':' '{print $2}')
    # Check if the time contains days (d)
    elif [[ $time =~ ^[0-9]+(d|day|days)$ ]]; then
        local days=$(echo "$time" | sed 's/[days]//g')
    # Check if the time contains hours (h)
    elif [[ $time =~ ^[0-9]+(h|hour|hours)$ ]]; then
        local hours=$(echo "$time" | sed 's/[hours]//g')
    # Check if the time contains minutes (m or min)
    elif [[ $time =~ ^[0-9]+(m|min|minute|minutes)$ ]]; then
        local minutes=$(echo "$time" | sed 's/[minutes]//g')
    # Check if the time contains seconds (s)
    elif [[ $time =~ ^[0-9]+(s|sec|second|secondes)$ ]]; then
        local seconds=$(echo "$time" | sed 's/[secondes]//g')
    # Handle other formats or seconds-only case
    else
        ((total_seconds = time))
        echo "$total_seconds"
        return 0
    fi

    # Ensure values are in base-10 (decimal)
    days=$((10#$days))
    hours=$((10#$hours))
    minutes=$((10#$minutes))
    seconds=$((10#$seconds))

    # Calculating the total seconds
    total_seconds=$((days * 24 * 60 * 60 + hours * 60 * 60 + minutes * 60 + seconds))
    echo "$total_seconds"
}

function get_jobs_with_time() {
    local output="$1"
    local time=$(convert_to_seconds "$2")
    local time_remaining="$3" # should be 0 or 1

    echo "$output" | while IFS= read -r line; do
        # Extract relevant columns
        job_id=$(echo "$line" | awk '{print $1}')
        job_state=$(echo "$line" | awk '{print $7}')
        job_duration=$(echo "$line" | awk '{print $4}')
        job_duration_seconds=$(convert_to_seconds "$job_duration")
        job_remaining=$(echo "$line" | awk '{print $5}')
        job_remaining_seconds=$(convert_to_seconds "$job_remaining")

        # Check conditions and perform actions
        if [[ "$job_state" == "R" ]]; then
            if [[ "$time_remaining" -eq "0" ]]; then
                if [[ "$job_duration_seconds" -gt "$time" ]]; then
                    echo "$line"
                fi
            else
                if [[ "$job_remaining_seconds" -gt "$time" ]]; then
                    echo "$line"
                fi
            fi
        fi
    done
}

function my_scancel() {
    dryrun=1
    pattern=""
    inverse_pattern=0
    time=""
    inverse_time=0
    if [ $# -eq 0 ]
    then
        echo "No arguments supplied, this command will cancel ALL your jobs!"
        n_total=$(_squeue_helper | grep -E -c "$USER" )
        ask_permission "$n_total" "$n_total"
        if [[ $REPLY =~ ^[Yy]$ ]]
        then
            scancel -u $USER
        fi
        return
    fi
    while test $# -gt 0; do
        case "$1" in
            -h | --help)
                echo "Usage: my_scancel [option...]" >&2
                echo "   -h, --help             Show this help message"
                echo "   -p, --pattern [text]   Pattern to match using grep (cancels all jobs that match this pattern)"
                echo "   -ip, --inverse_pattern Invert the pattern, so now the command will KEEP jobs that match the pattern"
                echo "   -t, --time [time]      Stop jobs with execution time greater than this value (d-hh:mm:ss, hh:mm:ss, mm:ss, s or #d, #h, #m)"
                echo "   -it, --inverse_time    Stop jobs with remaining time greater than the time passed with --time"
                echo "   -nd, --no_dryrun       Don't show jobs in dry run mode (dangerous)"
                echo ""
                echo "Description:"
                echo "   This fundtion provides a flexible way to cancel jobs on a cluster based on different criteria."
                echo "   Use the options to specify patterns, time limits, and dry run behavior."
                echo ""
                echo "Examples:"
                echo "   1. Cancel all jobs that contain the pattern 'experiment':"
                echo "      my_scancel -p experiment"
                echo ""
                echo "   2. Cancel all jobs that DON'T contain the pattern 'experiment':"
                echo "      my_scancel -p experiment -ip"
                echo ""
                echo "   3. Cancel jobs with execution time exceeding 1 hour:"
                echo "      my_scancel -t 01:00:00"
                echo "      my_scancel -t 1h"
                echo ""
                echo "   4. Cancel jobs with remaining time exceeding than 2 days:"
                echo "      my_scancel -t 2-00:00:00 -it"
                echo "      my_scancel -t 2d -it"
                echo ""
                echo "   5. Cancel all jobs:"
                echo "      5.1 with a dry run preview:"
                echo "          my_scancel"
                echo "      5.2 without displaying a dry run preview:"
                echo "          my_scancel -nd"
                echo ""
                echo "   6. It is possible to cancel jobs with pattern and time constrain:"
                echo "      my_scancel -p pattern -t 2d"
                echo "      my_scancel -p pattern -ip -t 2d -it"
                return
                ;;
            -p | --pattern)
                shift
                pattern=$1
                shift
                ;;
            -ip | --inverse_pattern)
                inverse_pattern=1
                shift
                ;;
            -t | --time)
                shift
                time=$1
                shift
                ;;
            -it | --inverse_time)
                inverse_time=1
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

    # if pattern is specified, get jobs with pattern
    if [ -n "$pattern" ]; then
        # Define the grep parameters
        grep_params="-E"
        if [ $inverse_pattern -eq 1 ]
        then
            grep_params="-v $grep_params"
        fi

        # get jobs that match pattern or the ones that do NOT match the pattern
        jobs_to_cancel=$(_squeue_helper | grep ${grep_params} "$pattern")
    else
        jobs_to_cancel=$(_squeue_helper)
    fi

    # if time is specified, get jobs that match time requirements
    if [ -n "$time" ]; then
        jobs_to_cancel=$(get_jobs_with_time "$jobs_to_cancel" "$time" "$inverse_time")
    fi

    n_total=$(_squeue_helper | grep -wc "$USER")
    n_jobs_to_cancel=$(echo "$jobs_to_cancel" | grep -wc "$USER")
    n_jobs_to_keep=$((n_total - n_jobs_to_cancel))

    if [ $dryrun -eq 1 ]
    then
        echo "[DRYRUN] Number of jobs before cancel: $n_total"
        if [ $inverse_pattern -eq 1 ]
        then
            echo "[DRYRUN][INVERSE] The following jobs are the ones that will REMAIN all the other jobs will be canceled!!"
        else
            echo "[DRYRUN] The following jobs are the ones that WILL be killed"
        fi
        echo ""
        if [ -n "$time" ]; then
            jobs_tmp=$(_squeue_helper | grep -E "$pattern")
            get_jobs_with_time "$jobs_tmp" "$time" "$inverse_time"
        else
            _squeue_helper | grep -E "$pattern"
        fi
        echo "[DRYRUN] Number of jobs after cancel: $n_jobs_to_keep/$n_total"
    fi
    echo ""

    ask_permission "$n_jobs_to_cancel" "$n_total"
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo ""
        echo "Canceling jobs..."
        echo "$jobs_to_cancel" |  awk '{print $1}' | xargs scancel
        echo "Waiting a bit for jobs to cancel..."
        
        # Set the start time
        start_time=$(date +%s)
        # Define the maximum wait time in seconds (e.g., 10 seconds)  
        max_wait_time=10
        n_jobs=$(_squeue_helper | grep -E -c "$USER")
        while [[ $n_jobs_to_keep -ne $n_jobs ]]; do
            current_time=$(date +%s)
            elapsed_time=$((current_time - start_time))
             
            if [ $elapsed_time -ge $max_wait_time ]; then
                echo "Timeout reached..."
                break
            fi
             
            # Update the number of total jobs
            n_jobs=$(_squeue_helper | grep -E -c "$USER")
             
            # Sleep for a short duration before checking again
            sleep 1
        done
        n_jobs=$(_squeue_helper | grep -E -c "$USER" )
        echo "Number of jobs after cancel: $n_jobs"
    fi
}
