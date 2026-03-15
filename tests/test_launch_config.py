from bi_validator.schemas.run import InlineDashboardConfigInput, LaunchLoginStep, RunLaunchRequest
from bi_validator.services.dashboard_validation import DashboardValidationCoordinator


def test_inline_launch_request_resolves_credentials_into_login_steps():
    request = RunLaunchRequest(
        dashboard_name="Sales Overview",
        dashboard_url="https://example.com/dashboard",
        platform="generic",
        inline_dashboard_config=InlineDashboardConfigInput(
            login_steps=[
                LaunchLoginStep(action="goto", value="https://example.com/login"),
                LaunchLoginStep(action="fill", selector="#user", credential_key="username"),
                LaunchLoginStep(action="fill", selector="#pass", credential_key="password"),
                LaunchLoginStep(action="click", selector="button[type='submit']"),
                LaunchLoginStep(action="wait_for", selector="[data-testid='dashboard-root']"),
            ],
            back_selectors=["button[aria-label='Back']"],
        ),
        credentials={"username": "alice@example.com", "password": "secret"},
    )

    config = DashboardValidationCoordinator()._resolve_dashboard_config(request)

    assert config.url == "https://example.com/dashboard"
    assert config.login_steps[0].value == "https://example.com/login"
    assert config.login_steps[1].value == "alice@example.com"
    assert config.login_steps[2].value == "secret"
    assert config.back_selectors == ["button[aria-label='Back']"]
