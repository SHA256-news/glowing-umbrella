# Contributing to glowing-umbrella

Thank you for your interest in contributing to the glowing-umbrella project! This guide provides comprehensive instructions for both human and automated contributors, including AI agents and automated systems.

## Table of Contents

- [General Guidelines](#general-guidelines)
- [AI Agents and Automated Systems](#ai-agents-and-automated-systems)
- [Development Environment](#development-environment)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Security Considerations](#security-considerations)

## General Guidelines

### Code of Conduct

- Be respectful and professional in all interactions
- Focus on constructive feedback and collaboration
- Ensure all contributions align with the project's goals and architecture

### Before Contributing

1. Check existing issues and pull requests to avoid duplicates
2. Read this entire contributing guide
3. Understand the project structure and dependencies
4. Set up the development environment properly

## AI Agents and Automated Systems

### Special Instructions for AI Contributors

This section provides specific guidelines for AI agents, automated systems, and AI-assisted development tools.

#### Core Principles for AI Contributors

1. **Minimal Changes**: Make the smallest possible changes to achieve the desired outcome
2. **Context Awareness**: Always understand the full project context before making changes
3. **Safety First**: Never commit secrets, credentials, or sensitive information
4. **Test Thoroughly**: Validate all changes with appropriate testing
5. **Respect Existing Patterns**: Follow established code patterns and conventions

#### AI Agent Workflow

1. **Analysis Phase**
   - Examine the entire repository structure
   - Understand dependencies and their purposes
   - Review existing code patterns and conventions
   - Identify the scope of required changes

2. **Planning Phase**
   - Create a detailed plan with minimal changes
   - Identify potential impacts and side effects
   - Plan testing strategy
   - Document the approach clearly

3. **Implementation Phase**
   - Make incremental, focused changes
   - Test each change immediately
   - Commit frequently with clear messages
   - Monitor for any breaking changes

4. **Validation Phase**
   - Run all existing tests
   - Verify functionality manually if applicable
   - Check for any unintended side effects
   - Ensure code quality standards are met

#### Automated System Guidelines

- **Environment Setup**: Always use virtual environments for Python dependencies
- **Dependency Management**: Use `pip install -r requirements.txt` for consistent setup
- **Code Quality**: Run linters and formatters before submitting changes
- **Documentation**: Update documentation for any user-facing changes
- **Rollback Plan**: Ensure changes can be easily reverted if needed

#### AI-Specific Restrictions

- Never modify the LICENSE file without explicit authorization
- Do not change core project configuration without clear justification
- Avoid making assumptions about user intent beyond the stated requirements
- Do not add unnecessary dependencies or complexity
- Respect rate limits when interacting with external APIs (EventRegistry, Google AI, Twitter)

#### Error Handling for AI Systems

- Implement proper error handling for API interactions
- Log meaningful error messages for debugging
- Fail gracefully when external services are unavailable
- Provide clear error messages for troubleshooting

## Development Environment

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git for version control

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/SHA256-news/glowing-umbrella.git
   cd glowing-umbrella
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Project Dependencies

The project includes the following key dependencies:
- `eventregistry`: For event and news data processing
- `google-generativeai`: For Google AI integration
- `tweepy`: For Twitter API interactions

## Code Standards

### Python Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Write docstrings for all functions and classes
- Keep functions small and focused
- Use type hints where appropriate

### File Organization

- Keep related functionality in logical modules
- Use descriptive file names
- Maintain consistent directory structure
- Update .gitignore for new file types as needed

### Documentation Standards

- Write clear, concise comments
- Document complex algorithms and business logic
- Keep README.md updated with any new features
- Include usage examples for new functionality

## Testing

### Testing Philosophy

- Write tests for all new functionality
- Maintain or improve test coverage
- Test edge cases and error conditions
- Include integration tests for external API interactions

### Running Tests

```bash
# Install test dependencies if needed
pip install pytest pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=.
```

### Test Guidelines for AI Systems

- Mock external API calls to avoid rate limits
- Test error conditions and edge cases
- Verify that API keys and secrets are not exposed
- Include tests for automated system integration

## Pull Request Process

### Before Submitting

1. Ensure all tests pass
2. Update documentation if needed
3. Check that changes are minimal and focused
4. Verify no secrets or credentials are included

### PR Requirements

- **Clear Title**: Descriptive title explaining the change
- **Detailed Description**: Explain what changed and why
- **Testing**: Describe how the change was tested
- **Breaking Changes**: Highlight any breaking changes
- **Related Issues**: Link to relevant issues

### Review Process

- All PRs require review before merging
- Address reviewer feedback promptly
- Ensure CI/CD checks pass
- Maintain clean commit history

## Issue Reporting

### Bug Reports

Include the following information:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
- Relevant error messages or logs

### Feature Requests

- Describe the proposed feature clearly
- Explain the use case and benefits
- Consider implementation complexity
- Discuss potential impact on existing functionality

### Security Issues

- Report security vulnerabilities privately
- Do not include sensitive information in public issues
- Follow responsible disclosure practices

## Security Considerations

### For AI Agents and Automated Systems

1. **API Key Management**
   - Never commit API keys or secrets to the repository
   - Use environment variables for sensitive configuration
   - Implement proper key rotation procedures
   - Monitor for accidental key exposure

2. **Data Privacy**
   - Handle user data responsibly
   - Implement appropriate data retention policies
   - Ensure compliance with privacy regulations
   - Sanitize logs and error messages

3. **External API Security**
   - Validate all external API responses
   - Implement rate limiting and retry logic
   - Use secure communication protocols (HTTPS)
   - Monitor for unusual API usage patterns

4. **Code Security**
   - Validate all user inputs
   - Avoid code injection vulnerabilities
   - Keep dependencies updated
   - Regular security audits of automated systems

### Incident Response

- Report security incidents immediately
- Document all security-related changes
- Follow incident response procedures
- Coordinate with security team when applicable

## Additional Resources

- [Python PEP 8 Style Guide](https://pep8.org/)
- [EventRegistry Documentation](https://eventregistry.org/documentation)
- [Google AI Documentation](https://ai.google.dev/)
- [Twitter API Documentation](https://developer.twitter.com/en/docs)

## Questions and Support

If you have questions about contributing or need help with the development process, please:

1. Check existing documentation and issues
2. Create a new issue with the "question" label
3. Be specific about what you need help with
4. Include relevant context and examples

Thank you for contributing to glowing-umbrella! Your automated and AI-assisted contributions help make this project better for everyone.