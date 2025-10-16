# Enhanced Timeout Summary Command

## Description
Provides a cumulative summary of conversation tasks from the last `/timeout` call to present, focusing on completed actions across conversation segments and compacted content. Builds progressive project summaries across multiple conversation sessions.

## Usage
```
/timeout
```

## Command Implementation
```javascript
// Find the last /timeout command in conversation history
const lastTimeoutIndex = findLastTimeoutCommand();
const analysisStartPoint = lastTimeoutIndex + 1; // Exclude the timeout call itself

// Analyze conversation from last timeout to present
const conversationSegment = getConversationFromIndex(analysisStartPoint);
const compactedContent = extractCompactedConversations(conversationSegment);
const currentContent = extractCurrentConversation(conversationSegment);

// Extract completed tasks from all sources
const completedTasks = [
    ...extractCompletedActions(compactedContent),
    ...extractCompletedActions(currentContent)
];

const taskGroups = groupSimilarTasks(completedTasks);
const deduplicatedTasks = removeDuplicateTasks(taskGroups);

// Generate bulleted summary
const summary = deduplicatedTasks.map(group => {
    return formatTaskBullet(group);
});

function findLastTimeoutCommand() {
    // Search conversation history for last "/timeout" occurrence
    // Return index of that command, or -1 if no previous timeout found
    const history = getConversationHistory();
    for (let i = history.length - 1; i >= 0; i--) {
        if (history[i].content.includes('/timeout')) {
            return i;
        }
    }
    return -1; // No previous timeout found - analyze entire conversation
}

function extractCompactedConversations(segment) {
    // Parse any compacted conversation summaries within the segment
    // Look for patterns like "Previous conversation summary:" or compact markers
    const compactedSummaries = [];
    
    segment.forEach(message => {
        if (isCompactedContent(message)) {
            compactedSummaries.push(parseCompactedTasks(message));
        }
    });
    
    return compactedSummaries.flat();
}

function removeDuplicateTasks(taskGroups) {
    // Remove duplicate or very similar tasks that might appear
    // across compacted content and current conversation
    const seen = new Set();
    return taskGroups.filter(task => {
        const taskSignature = generateTaskSignature(task);
        if (seen.has(taskSignature)) {
            return false;
        }
        seen.add(taskSignature);
        return true;
    });
}

function formatTaskBullet(taskGroup) {
    // Requirements:
    // - Clear, simple, past tense
    // - Start with key concept/idea
    // - No "I" statements
    // - Focus on what was completed/changed
    // - No technical details or file paths
    // - No category headers

    return bulletPoint;
}

return summary.join('\n');
```

## Enhanced Logic Flow
1. **Find Last Timeout**: Scan conversation history for the most recent `/timeout` command
2. **Define Analysis Range**: From after the last timeout (or conversation start) to current point
3. **Parse All Content**: Extract tasks from both compacted summaries and current conversation
4. **Deduplicate**: Remove redundant or duplicate completed tasks
5. **Format Output**: Generate clean bullet summary following existing rules

## Output Format
Generates 2-3 bullets for short segments, 4-6 for longer cumulative summaries:

### Example with Previous Timeout:
*Cumulative summary since last /timeout (3 days ago)*

• Authentication system integrated with JWT token validation and session management
• Database migration scripts created and deployed for user role management  
• Chat flow refactored into modular JavaScript components with error handling
• Test coverage expanded for critical user workflows and edge cases
• Performance monitoring dashboard implemented with real-time metrics
• API documentation updated to reflect new authentication patterns

### Example without Previous Timeout:
*No previous /timeout found - analyzing entire conversation*

• Database queries optimized with proper indexing strategy
• Error handling improved across API endpoints
• Documentation updated to reflect new architecture patterns

### Example with Compacted Content:
*Including tasks from compacted conversations*

• User authentication flow redesigned with OAuth integration
• Database schema refactored for improved performance and scalability
• Frontend components converted to TypeScript with proper type definitions
• CI/CD pipeline established with automated testing and deployment
• Error logging system implemented with structured monitoring

## Formatting Rules
- **Past tense only**: "Created", "Updated", "Fixed", not "Creating" or "Will create"
- **Action-focused**: What was actually done, not what was discussed
- **Concept-first**: Start with the main idea, not implementation details
- **No technical specifics**: Avoid file paths, function names, or code snippets
- **Grouped logically**: Similar tasks combined into single bullets
- **Clean bullets**: Use • symbol with single space
- **Cumulative scope**: Includes all completed work since last timeout checkpoint

## Key Enhancements
- **Cumulative Tracking**: Builds on previous timeout summaries rather than just current conversation
- **Cross-Segment Analysis**: Includes compacted conversation content and previous work
- **Smart Deduplication**: Prevents redundant task reporting across conversation segments
- **Timeline Awareness**: Understands conversation boundaries and checkpoint history
- **Fallback Behavior**: Handles conversations without previous timeouts gracefully
- **Progress Continuity**: Maintains project context across multiple conversation sessions

## Integration Notes
- Used before `/compact` for comprehensive project handoffs
- Maintains backward compatibility with original `/timeout` behavior
- Works seamlessly with conversation compaction for long-term project tracking
- Enables progressive project summaries across multiple Claude Code sessions
- Focuses on deliverables over process discussions
- Excludes planning, debugging discussions, or analysis
- Emphasizes business value and functional changes across entire project timeline

## Usage Scenarios
- **Project Handoffs**: Complete summary of work across multiple conversation sessions
- **Sprint Reviews**: Cumulative progress since last checkpoint
- **Status Updates**: What's been accomplished since last timeout
- **Session Continuity**: Bridging work across compacted conversations
- **Progress Tracking**: Long-term project development summaries