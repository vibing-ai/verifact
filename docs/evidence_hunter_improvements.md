# Enhanced Web Search Evidence Gathering

This document describes the enhanced web search capabilities implemented for the EvidenceHunter agent in the VeriFact system.

## Overview

The EvidenceHunter agent has been enhanced with improved web search capabilities, allowing for more accurate and comprehensive evidence gathering. The implementation now supports both the default OpenAI WebSearchTool and a custom Serper.dev integration, which can be selected through configuration.

## Key Improvements

1. **Dual Search Provider Support**

   - OpenAI WebSearchTool (default)
   - Serper.dev API integration (configurable)

2. **Enhanced Query Construction**

   - More detailed instructions for claim-based query formulation
   - Support for generating multiple search queries
   - Entity extraction and concept identification
   - Contradiction-seeking query generation

3. **Source Evaluation**

   - Source credibility assessment
   - Relevance scoring on a 0-1 scale
   - Stance classification (supporting, contradicting, neutral)
   - Passage extraction and selection

4. **Improved Result Processing**
   - Comprehensive evidence aggregation
   - Ranking by relevance and credibility
   - Source citation and documentation
   - Contradicting evidence identification

## Configuration

The search provider can be configured via environment variables:

```
# Search Configuration in .env file
USE_SERPER=false  # Set to true to use Serper.dev instead of WebSearchTool
SERPER_API_KEY=your_serper_api_key  # Only needed if USE_SERPER is true
```

## Implementation Details

### Search Tools

A new module `src/utils/search_tools.py` implements search provider functionality:

1. **SerperSearchTool**: Custom integration with the Serper.dev API

   - Support for general search, news, and image search
   - Configurable number of results
   - Error handling and logging
   - Response format normalization

2. **get_search_tool()**: Factory function to select the appropriate search tool
   - Uses `USE_SERPER` environment variable to determine which provider to use
   - Falls back to OpenAI's WebSearchTool when Serper is not configured

### EvidenceHunter Enhancements

The EvidenceHunter agent in `src/verifact_agents/evidence_hunter/hunter.py` has been updated with:

1. **Improved Agent Instructions**

   - More detailed guidance for search query formulation
   - Source credibility assessment instructions
   - Evidence selection criteria
   - Result formatting guidelines

2. **Enhanced Query Construction**

   - Richer context inclusion
   - Explicit search guidance
   - Multi-perspective searching

3. **Better Logging**
   - Information about search operations
   - Evidence gathering results
   - Performance metrics

## Using Serper.dev

To use Serper.dev as your search provider:

1. Sign up for an API key at [Serper.dev](https://serper.dev)
2. Add your API key to your `.env` file:
   ```
   USE_SERPER=true
   SERPER_API_KEY=your_serper_api_key
   ```
3. Restart the VeriFact system

## Testing

The implementation includes comprehensive tests:

1. **SerperSearchTool Tests**

   - API response handling
   - Error management
   - Configuration validation

2. **EvidenceHunter Tests**
   - Evidence gathering with enhanced instructions
   - Different search tool configurations
   - Result processing validation

## Future Improvements

1. **Multi-Provider Support**

   - Add support for additional search APIs
   - Implement result aggregation across providers

2. **Advanced Source Evaluation**

   - Domain credibility database
   - Publication date awareness
   - Author credibility assessment

3. **Semantic Search**

   - Implement vector-based search for better relevance
   - Support for concept matching beyond keyword search

4. **Language Support**
   - Multilingual search query generation
   - Cross-language evidence correlation
