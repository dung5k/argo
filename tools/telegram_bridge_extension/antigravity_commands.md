# Tài liệu các Command của Antigravity

Đây là danh sách các command khả dụng của extension Antigravity (Windsurf Agent), trích xuất qua `vscode.commands.getCommands(true)`.
Bạn có thể sử dụng các lệnh này trong `vscode.commands.executeCommand('tên_lệnh', tham_số)`.

## Chat & Agent Sidel Panel
- `antigravity.agentSidePanel.expandView`
- `antigravity.agentSidePanel.focus`
- `antigravity.agentSidePanel.open`
- `antigravity.agentSidePanel.removeView`
- `antigravity.agentSidePanel.resetViewLocation`
- `antigravity.agentSidePanel.toggleVisibility`
- `antigravity.sendPromptToAgentPanel`
- `antigravity.toggleChatFocus`
- `workbench.action.chat.assignSelectedAgent`
- `workbench.action.chat.setAgentSessionsOrientationAuto`
- `workbench.action.chat.setAgentSessionsOrientationSideBySide`
- `workbench.action.chat.setAgentSessionsOrientationStacked`

## Accept/Reject & Flow
- `antigravity.prioritized.agentAcceptAllInFile`
- `antigravity.prioritized.agentAcceptFocusedHunk`
- `antigravity.prioritized.agentFocusNextFile`
- `antigravity.prioritized.agentFocusNextHunk`
- `antigravity.prioritized.agentFocusPreviousFile`
- `antigravity.prioritized.agentFocusPreviousHunk`
- `antigravity.prioritized.agentRejectAllInFile`
- `antigravity.prioritized.agentRejectFocusedHunk`
- `antigravity.prioritized.explainProblem`
- `antigravity.prioritized.supercompleteAccept`
- `antigravity.prioritized.supercompleteEscape`

## Workflow & Rules
- `antigravity.createGlobalWorkflow`
- `antigravity.createRule`
- `antigravity.createWorkflow`
- `antigravity.openRulesEducationalLink`

## Import & Settings
- `antigravity.editorModeSettings`
- `antigravity.importCiderSettings`
- `antigravity.importCursorExtensions`
- `antigravity.importCursorSettings`
- `antigravity.importVSCodeExtensions`
- `antigravity.importVSCodeRecentWorkspaces`
- `antigravity.importVSCodeSettings`
- `antigravity.importWindsurfExtensions`
- `antigravity.importWindsurfSettings`
- `antigravity.migrateWindsurfSettings`
- `antigravity.openConfigurePluginsPage`
- `antigravity.openMcpConfigFile`
- `antigravity.openQuickSettingsPanel`
- `antigravity.toggleSettingsDevTools`
- `workbench.action.openAntigravitySettings`
- `workbench.action.openAntigravitySettingsWithId`
- `workbench.action.showAntigravityStatusBarSettings`

## Dev Container & Remote
- `antigravity-dev-containers.attachToRunningContainer`
- `antigravity-dev-containers.openInContainer`
- `antigravity-dev-containers.reopenFolderLocally`
- `antigravity-dev-containers.reopenInContainer`
- `antigravity-dev-containers.showLog`
- `antigravitySSHHosts.expandView`
- `antigravitySSHHosts.focus`
- `antigravitySSHHosts.open`
- `antigravitySSHHosts.resetViewLocation`
- `antigravityWslTargets.expandView`
- `antigravityWslTargets.focus`
- `antigravityWslTargets.open`
- `antigravityWslTargets.resetViewLocation`
- `workbench.action.output.show.extension-output-google.antigravity-dev-containers-#1-Remote - Dev Containers (Antigravity)`

## Terminal & Commands
- `antigravity.onManagerTerminalCommandData`
- `antigravity.onManagerTerminalCommandFinish`
- `antigravity.onManagerTerminalCommandStart`
- `antigravity.onShellCommandCompletion`
- `antigravity.readTerminal`
- `antigravity.sendTerminalToSidePanel`
- `antigravity.showManagedTerminal`
- `antigravity.updateTerminalLastCommand`

## View & Navigation
- `antigravity-dev-containers.openInContainer`
- `antigravity-dev-containers.reopenFolderLocally`
- `antigravity-dev-containers.reopenInContainer`
- `antigravity.openAgent`
- `antigravity.openBrowser`
- `antigravity.openChangeLog`
- `antigravity.openConfigurePluginsPage`
- `antigravity.openConversationPicker`
- `antigravity.openConversationWorkspaceQuickPick`
- `antigravity.openCustomizationsTab`
- `antigravity.openDiffZones`
- `antigravity.openDocs`
- `antigravity.openGenericUrl`
- `antigravity.openInCiderAction.topBar`
- `antigravity.openInteractiveEditor`
- `antigravity.openIssueReporter`
- `antigravity.openMcpConfigFile`
- `antigravity.openMcpDocsPage`
- `antigravity.openPersistentLanguageServerLog`
- `antigravity.openQuickSettingsPanel`
- `antigravity.openReviewChanges`
- `antigravity.openRulesEducationalLink`
- `antigravity.openTroubleshooting`
- `antigravityDevContainers.open`
- `antigravitySSHHosts.open`
- `antigravityWslTargets.open`
- `workbench.action.openAntigravityExtensionLogsFolder`
- `workbench.action.openAntigravitySettings`
- `workbench.action.openAntigravitySettingsWithId`
- `workbench.action.openInAgentManager`

## Git
- `git.antigravityClearCloneProgress`
- `git.antigravityCloneNonInteractive`
- `git.antigravityGetRemoteUrl`
- `git.antigravityReportCloneProgress`

## Khác (Others)
- `agent.postOnboarding.reset`
- `antigravity.acceptAgentStep`
- `antigravity.acceptCompletion`
- `antigravity.agentViewContainerId`
- `antigravity.agentViewContainerId.resetViewContainerLocation`
- `antigravity.artifacts.startComment`
- `antigravity.cancelGenerateCommitMessage`
- `antigravity.cancelLogin`
- `antigravity.cancelSnoozeAutocomplete`
- `antigravity.captureTraces`
- `antigravity.clearAndDisableTracing`
- `antigravity.closeAllDiffZones`
- `antigravity.customizeAppIcon`
- `antigravity.downloadDiagnostics`
- `antigravity.enableTracing`
- `antigravity.endDemoMode`
- `antigravity.explainAndFixProblem`
- `antigravity.generateCommitMessage`
- `antigravity.getBrowserOnboardingPort`
- `antigravity.getDiagnostics`
- `antigravity.getLintErrors`
- `antigravity.getManagerTrace`
- `antigravity.getWorkbenchTrace`
- `antigravity.handleAuthRefresh`
- `antigravity.hideFullScreenView`
- `antigravity.isFileGitIgnored`
- `antigravity.killLanguageServerAndReloadWindow`
- `antigravity.killRemoteExtensionHost`
- `antigravity.logObservabilityDataAction`
- `antigravity.manager.onboarding.reset`
- `antigravity.onboarding.reset`
- `antigravity.playAudio`
- `antigravity.playNote`
- `antigravity.rejectAgentStep`
- `antigravity.reloadAgentSidePanel`
- `antigravity.reloadWindow`
- `antigravity.resetOnboardingBackend`
- `antigravity.restartLanguageServer`
- `antigravity.restartMainLanguageServer`
- `antigravity.sendAnalyticsAction`
- `antigravity.setDiffZonesState`
- `antigravity.showAuthFailureFullScreenView`
- `antigravity.showBrowserAllowlist`
- `antigravity.showLanguageServerCrashFullScreenView`
- `antigravity.showLanguageServerInitFailureFullScreenView`
- `antigravity.showSshDisconnectionFullScreenView`
- `antigravity.sidecar.sendDiffZone`
- `antigravity.simulateSegFault`
- `antigravity.snoozeAutocomplete`
- `antigravity.startDemoMode`
- `antigravity.startNewConversation`
- `antigravity.startVoiceRecording`
- `antigravity.stopVoiceRecording`
- `antigravity.switchBetweenWorkspaceAndAgent`
- `antigravity.tabReporting`
- `antigravity.toggleDebugInfoWidget`
- `antigravity.toggleManagerDevTools`
- `antigravity.toggleModelSelector`
- `antigravity.togglePersistentLanguageServer`
- `antigravity.togglePlanningModeSelector`
- `antigravity.toggleRerenderFrequencyAlerts`
- `antigravity.trackBackgroundConversationCreated`
- `antigravity.updateDebugInfoWidget`
- `antigravity.uploadErrorAction`
- `antigravityAgentManager.clearErrors`
- `antigravityAgentManager.reportError`
- `antigravityAgentManager.reportNotification`
- `antigravityAgentManager.reportStatus`
- `antigravityDevContainers.expandView`
- `antigravityDevContainers.focus`
- `antigravityDevContainers.resetViewLocation`
- `workbench.action.focusAgentManager.continueConversation`
- `workbench.action.isAntigravitySnoozed`
- `workbench.action.output.show.google.antigravity.Antigravity`
- `workbench.action.output.show.google.antigravity.Antigravity Crash Logs`
- `workbench.action.output.show.jetski.antigravity-interactive-editor`
- `workbench.action.registerAntigravityStatusBarItemPosition`
- `workbench.antigravity.showLaunchpad`

