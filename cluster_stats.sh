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
echo ""
echo ""

# Output detailed usage
echo "DETAILED: CPU and GPU usage per year"
for year in $(seq "$START_YEAR" "$END_YEAR")
do
    if [[ -n "$USER" ]]; then
        FILTER="user=$USER"
    else
        FILTER=""
    fi

    CPU_OUTPUT=$(sreport cluster AccountUtilizationByUser account=$ACCOUNT $FILTER start=${year}-01-01 end=${year}-12-31 -t hours -nP)
    GPU_OUTPUT=$(sreport cluster AccountUtilizationByUser account=$ACCOUNT $FILTER start=${year}-01-01 end=${year}-12-31 -t hours --tres="gres/gpu" -nP)

    # Check if there is output to display
    if [[ -n "$CPU_OUTPUT" || -n "$GPU_OUTPUT" ]]; then
        echo "Year: $year"
        if [[ -n "$CPU_OUTPUT" ]]; then
            echo "CPU Usage:"
            echo "$CPU_OUTPUT" | awk -F'|' 'NR > 1 {print "(" $1 ") User: " $3 " (" $4 ") used " $5 " CPU hours"}'
        fi
        echo ""
        if [[ -n "$GPU_OUTPUT" ]]; then
            echo "GPU Usage:"
            echo "$GPU_OUTPUT" | awk -F'|' 'NR > 1 {print "(" $1 ") User: " $3 " (" $4 ") used " $6 " GPU hours"}'
        fi
        echo ""
    fi
done

# Output summary usage
echo -e "\n\nSUMMARY: CPU and GPU usage for ALL users in $ACCOUNT"
for year in $(seq "$START_YEAR" "$END_YEAR")
do

    CPU_OUTPUT=$(sreport cluster AccountUtilizationByUser account=$ACCOUNT start=${year}-01-01 end=${year}-12-31 -t hours -nP)
    GPU_OUTPUT=$(sreport cluster AccountUtilizationByUser account=$ACCOUNT start=${year}-01-01 end=${year}-12-31 -t hours --tres="gres/gpu" -nP)

    # Check if there is output to display
    if [[ -n "$CPU_OUTPUT" || -n "$GPU_OUTPUT" ]]; then
        echo "Year: $year"
        if [[ -n "$CPU_OUTPUT" ]]; then
            echo "$CPU_OUTPUT" | awk -F'|' -v yr=$year 'NR==1 {print "(" $1 ") CPU usage in " yr " = " $5 " hours"}'
        fi
        if [[ -n "$GPU_OUTPUT" ]]; then
            echo "$GPU_OUTPUT" | awk -F'|' -v yr=$year 'NR==1 {print "(" $1 ") GPU usage in " yr " = " $6 " hours"}'
        fi
        echo ""
    fi
done