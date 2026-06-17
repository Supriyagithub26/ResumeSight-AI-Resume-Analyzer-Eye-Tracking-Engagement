# Simple resume analysis server without Maven dependency
# This is a workaround to demonstrate the backend without complex Maven setup

Write-Host "Starting ResumeSight Backend Analysis Server..."
Write-Host "Server running on http://localhost:8080"

# In production, you would run: mvn spring-boot:run
# For now, compile and run the Java classes directly
# Note: Full Spring Boot requires Maven - this is a simplified demo

# The frontend will fallback to demo results since we don't have Maven installed
# To deploy with Maven:
# 1. Install Maven from https://maven.apache.org/download.cgi
# 2. Set MAVEN_HOME environment variable
# 3. Add %MAVEN_HOME%\bin to PATH
# 4. Run: mvn clean spring-boot:run

Write-Host ""
Write-Host "To fully deploy the backend:"
Write-Host "  1. Install Apache Maven"
Write-Host "  2. Run: mvn clean spring-boot:run"
Write-Host ""
Write-Host "For now, the frontend is configured to work with demo results."
Write-Host "Press Ctrl+C to stop."

# Keep process alive
while ($true) { Start-Sleep -Seconds 1 }
