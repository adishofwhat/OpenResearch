# 1. Initialize research
$baseUrl = "http://localhost:8001"
$body = @{
    query = "What is AI?"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$baseUrl/research/init/" -Method Post -Body $body -ContentType "application/json"
$sessionId = $response.session_id

# 2. Wait a moment and get the clarification questions
Start-Sleep -Seconds 2
$questions = Invoke-RestMethod -Uri "$baseUrl/research/$sessionId/questions" -Method Get

# 3. Provide answers to the questions
$answers = @{
    "Could you provide more context about what aspects of 'What is AI?' you're most interested in?" = "I'm interested in machine learning and neural networks"
    "What specific information about 'What is AI?' would be most valuable to you?" = "Understanding the basic concepts and current applications"
    "Are you looking for recent developments in 'What is AI?' or historical background?" = "Both historical context and recent developments"
} | ConvertTo-Json

$clarifyResponse = Invoke-RestMethod -Uri "$baseUrl/research/$sessionId/clarify" -Method Post -Body $answers -ContentType "application/json"

# 4. Start the research process
$startResponse = Invoke-RestMethod -Uri "$baseUrl/research/$sessionId/start" -Method Post

# 5. Monitor progress
do {
    Start-Sleep -Seconds 2
    $status = Invoke-RestMethod -Uri "$baseUrl/research/$sessionId/status" -Method Get
    Write-Host "Status: $($status.status) - Progress: $($status.progress)"
} while ($status.status -ne "completed" -and $status.status -ne "error")

# 6. Get final results when complete
$results = Invoke-RestMethod -Uri "$baseUrl/research/$sessionId/result" -Method Get
$results | ConvertTo-Json -Depth 10

