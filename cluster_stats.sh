#!/bin/bash

# Parse input arguments
START_YEAR="2019"
END_YEAR="2024"
ACCOUNT="kalousis"
USER=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --start-year) START_YEAR="$2"; shift ;;
        --end-year) END_YEAR="$2"; shift ;;
        --account) ACCOUNT="$2"; shift ;;
        --user) USER="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Display the parameters being used
echo "Running report with the following parameters:"
echo "Start Year: $START_YEAR"
echo "End Year: $END_YEAR"
echo "Account: $ACCOUNT"
[[ -n "$USER" ]] && echo "User: $USER" || echo "User: All users"
echo "--------------------------------"

# Output detailed usage
echo "DETAILED: CPU and GPU usage per year"
for year in $(seq "$START_YEAR" "$END_YEAR")
do
    echo "Year: $year"
    if [[ -n "$USER" ]]; then
        FILTER="user=$USER"
    else
        FILTER=""
    fi
    echo "CPU Usage:"
    sreport cluster AccountUtilizationByUser account=$ACCOUNT $FILTER start=${year}-01-01 end=${year}-12-31 -t hours -nP
    echo "GPU Usage:"
    sreport cluster AccountUtilizationByUser account=$ACCOUNT $FILTER start=${year}-01-01 end=${year}-12-31 -t hours --tres="gres/gpu" -nP
    echo "--------------------------------"
done

# Output summary usage
echo -e "\n\nSUMMARY: CPU and GPU usage per year"
for year in $(seq "$START_YEAR" "$END_YEAR")
do
    echo "Year: $year"
    if [[ -n "$USER" ]]; then
        FILTER="user=$USER"
    else
        FILTER=""
    fi
    sreport cluster AccountUtilizationByUser account=$ACCOUNT $FILTER start=${year}-01-01 end=${year}-12-31 -t hours -nP | \
    awk -F'|' -v yr=$year 'NR==1 {print "(" $1 ") CPU usage in " yr " = " $5 " hours"}'
    sreport cluster AccountUtilizationByUser account=$ACCOUNT $FILTER start=${year}-01-01 end=${year}-12-31 -t hours --tres="gres/gpu" -nP | \
    awk -F'|' -v yr=$year 'NR==1 {print "(" $1 ") GPU usage in " yr " = " $6 " hours"}'
    echo "--------------------------------"
done
