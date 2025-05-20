# VeriFact Testing Action Plan

Based on the findings from the end-to-end testing, here's a prioritized action plan to resolve the identified issues and properly test the VeriFact platform.

## 1. Fix Environment Setup Issues

### Critical Dependencies

1. **OpenAI Agents SDK Issue**

   - The error `No module named 'openai.agents'` indicates a compatibility issue with OpenAI SDK
   - According to pyproject.toml, there's a dependency on a separate package `openai-agents`
   - Install the missing package: `pip install openai-agents`
   - Check compatibility between openai v1.79.0 and the openai-agents package

2. **Create and Configure .env File**

   - Create a proper .env file based on the template in the README
   - Ensure all required environment variables are set:

     ```
     # OpenRouter API key (required for model access)
     OPENROUTER_API_KEY=your_key_here
     OPENROUTER_SITE_URL=http://localhost:8000
     OPENROUTER_SITE_NAME=VeriFact-Testing

     # Search tools
     SERPER_API_KEY=your_key_here
     USE_SERPER=true

     # Supabase integration
     SUPABASE_URL=your_url_here
     SUPABASE_KEY=your_key_here
     SUPABASE_DB_URL=your_url_here

     # Authentication
     CHAINLIT_AUTH_SECRET=your_secret_here
     VERIFACT_ADMIN_USER=admin
     VERIFACT_ADMIN_PASSWORD=secure_password
     VERIFACT_DEMO_USER=demo
     VERIFACT_DEMO_PASSWORD=secure_password
     CHAINLIT_PERSIST=true
     ```

3. **Install Missing Packages**
   - Install the missing chainlit package: `pip install chainlit>=1.0.600`
   - Verify all required dependencies are installed: `pip install -e .` or `pip install -r requirements.txt`

## 2. Service Startup and Verification

1. **Start Docker Services**

   - Start Docker Desktop application
   - Verify it's running with: `docker info`
   - Once .env file is in place, validate Docker Compose configuration: `docker-compose config`

2. **Start API Server**
   - Start the API server manually for testing: `cd src && uvicorn main:app --reload`
   - Verify it's running by accessing: `http://localhost:8000/docs`
   - Test the API endpoints using the test_api.py script

## 3. Component Testing

Once the environment is properly set up:

1. **Test Individual Components**

   - Run: `./test_claim_detector.py`
   - Run: `./test_evidence_hunter.py`
   - Run: `./test_verdict_writer.py`
   - Fix any component-specific issues that arise

2. **Test Pipeline Integration**
   - Run: `./test_pipeline_integration.py`
   - Verify all components work together properly

## 4. System Testing

1. **Docker Deployment**

   - Once all components are working, test full Docker deployment:
   - `docker-compose down && docker-compose up -d`
   - Verify all services start correctly

2. **UI Testing**
   - Start the Chainlit UI: `chainlit run app.py`
   - Verify the UI works correctly at: `http://localhost:8000`
   - Test interactions, factchecking process, and all UI elements

## 5. Performance and Stress Testing

Once the system is fully functional:

1. **Run Performance Tests**

   - Test response times for different inputs
   - Verify the <30 second target for single claim processing
   - Test with multiple claims and verify proper handling

2. **Stress Testing**
   - Test the system under load with simultaneous requests
   - Verify resource usage and identify bottlenecks

## 6. Monitoring and Final Verification

1. **Monitor System During Tests**

   - Monitor resource usage during testing
   - Check logs for errors or warnings
   - Identify any performance bottlenecks

2. **Complete Testing Report**
   - Document all test results
   - Create a comprehensive report of findings
   - Provide recommendations for improvements

## Expected Outcome

After completing this action plan, we should have:

1. A fully functional VeriFact platform with all components working correctly
2. Comprehensive test results documenting the performance and functionality
3. Clear understanding of any remaining issues or areas for improvement

## Timeline

This action plan should be executed in the order presented, with each section dependent on the successful completion of the previous section. The entire process may take 1-2 days depending on the complexity of resolving the identified issues.
