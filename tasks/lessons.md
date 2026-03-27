# Opencode Global Rules

## 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

## 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

## 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

## 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

## 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

## 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## 7. General Programming Principles

### Core Principles
- **Functional Completeness**: Consider all input types and edge cases
- **Configuration Simplification**: Avoid complex dependencies, use defaults
- **Error Handling**: Provide meaningful error messages
- **Performance Awareness**: Evaluate processing time and resource usage
- **User Experience**: Ensure code is easy to use and maintain
- **Documentation Priority**: Provide clear usage instructions
- **Test-Driven Development**: Write tests before implementation
- **Intelligent Fallback**: Auto-select optimal processing

### General Considerations Checklist
- ✅ Input validation and parameter checking
- ✅ Edge case handling (min/max values, empty inputs)
- ✅ Dependency management and installation requirements
- ✅ Error handling with specific solutions
- ✅ Performance optimization and limitations
- ✅ User-friendly interfaces and documentation
- ✅ Test coverage for various input types
- ✅ Complete documentation and guides
- ✅ Simplified configuration
- ✅ Intelligent decision making
- ✅ Fault tolerance and fallback mechanisms
- ✅ Resource management and cleanup
- ✅ Detailed logging for debugging
- ✅ Version compatibility
- ✅ Security considerations
- ✅ Code maintainability and modularity
- ✅ Architectural scalability

### Best Practices
- **User-centric approach**: Consider user experience and problems
- **Test-first development**: Write tests before implementation
- **Simplified configuration**: Reduce external dependencies
- **Complete functionality**: Cover all input scenarios
- **Documentation focus**: Clear usage instructions
- **Performance awareness**: Consider processing time
- **Error handling**: Meaningful error messages
- **User experience**: Easy to use and maintain

### Code Quality Checklist
- ✅ Input validation and edge cases
- ✅ Dependency management
- ✅ Error handling and feedback
- ✅ Performance evaluation
- ✅ User-friendliness and docs
- ✅ Test coverage
- ✅ Configuration simplification
- ✅ Intelligent decision making
- ✅ Fault tolerance
- ✅ Resource management
- ✅ Logging and debugging
- ✅ Version compatibility
- ✅ Security and permissions
- ✅ Code readability
- ✅ Architectural scalability

---
## Task Management
1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

---
## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.