# Save this as format-research-output.ps1

function Format-ResearchOutput {
    param (
        [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
        [PSObject]$ResearchResult
    )

    process {
        Clear-Host
        Write-Host "====================== RESEARCH QUERY ======================" -ForegroundColor Cyan
        Write-Host $ResearchResult.original_query -ForegroundColor Yellow
        Write-Host ""
        
        Write-Host "====================== SUB-QUESTIONS ======================" -ForegroundColor Cyan
        foreach ($question in $ResearchResult.sub_questions) {
            Write-Host "- $question" -ForegroundColor White
        }
        Write-Host ""
        
        Write-Host "====================== RETRIEVED DATA ======================" -ForegroundColor Cyan
        foreach ($item in $ResearchResult.retrieved_data) {
            Write-Host "- $item" -ForegroundColor Gray
        }
        Write-Host ""
        
        Write-Host "====================== SUMMARIES ======================" -ForegroundColor Cyan
        foreach ($summary in $ResearchResult.summaries) {
            Write-Host "- $summary" -ForegroundColor White
        }
        Write-Host ""
        
        Write-Host "====================== FINAL REPORT ======================" -ForegroundColor Green
        # Split the report by line breaks and print each line
        $reportLines = $ResearchResult.final_report -split "`n"
        foreach ($line in $reportLines) {
            # Check if line is a heading
            if ($line -match "^#+ ") {
                Write-Host $line -ForegroundColor Yellow
            }
            # Check if line is a bullet point
            elseif ($line -match "^- ") {
                Write-Host $line -ForegroundColor White
            }
            else {
                Write-Host $line -ForegroundColor Gray
            }
        }
    }
}

# Example usage:
# Invoke-RestMethod -Uri "http://localhost:8001/research/" -Method Post -Body $query -ContentType "application/json" | Format-ResearchOutput