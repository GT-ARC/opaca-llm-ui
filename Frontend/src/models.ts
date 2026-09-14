// --- Shared REST Request/Response Models ---

export interface ConnectRequest {
    url: string;
    user: string | null;
    pwd: string | null;
}

export interface DebugMessage {
    id: string;
    type?: string;
    text?: string;
    chatId?: string;
    [key: string]: any;
}

export interface InvokeRequest {
    action: string;
    agent: string;
    parameters: Record<string, any>;
}

export interface InvokeResponse {
    success: boolean;
    result: any | null;
    error: string | null;
}

export interface RestrictedActions {
    forbidden: string[];
    need_confirmation: string[];
}

export interface QueryRequest {
    user_query: string;
    streaming?: boolean;
    file_ids?: string[];
}

export interface MCPCreateRequest {
    type: string;
    server_url: string;
    server_label?: string;
    default_approval: ToolApprovalState;
    auth?: MCPAuthRequest;
}

export type MCPAuthType = "none" | "auto" | "oauth2" | "headers";

export interface MCPAuthRequest {
    auth_type: MCPAuthType;
    headers?: Record<string, string>;
    client_id?: string;
    client_secret?: string;
}

export interface ToolCall {
    id: string;
    type: "opaca" | "mcp" | "internal" | string;
    name: string;
    args: Record<string, any>;
    result: any | null;
}

export interface AgentMessage {
    id: string;
    agent: string;
    content: string;
    tools: ToolCall[];
    response_metadata: Record<string, any>;
    execution_time: number;
    formatted_output: any | null;
}

export interface QueryResponse {
    query: string;
    agent_messages: AgentMessage[];
    iterations: number;
    execution_time: number;
    content: string;
    error: string;
}

export interface PushMessage extends QueryResponse {
    task_id: number;
}

export interface ChatMessage {
    role: string;
    content: string | Record<string, any>[];
}

export interface Chat {
    chat_id: string;
    name: string;
    responses: QueryResponse[];
    time_created: string;
    time_modified: string;
    is_aborted: boolean;
    is_finished: boolean;
    active_files: string[];
}

export interface SearchResult {
    chat_id: string;
    chat_name: string;
    message_id: number;
    excerpt: string;
}

export interface OpacaFile {
    file_id: string;
    content_type: string;
    file_name: string;
    keywords: string[];
    host_ids: Record<string, string>;
}

export interface ScheduledTask {
    method: string;
    task_id: number;
    query: string;
    next_time: string;
    interval: number;
    repetitions: number;
}

export interface Prompt {
    question: string;
    icon: string | null;
}

export interface PromptCategory {
    id: string;
    header: string;
    icon: string | null;
    visible: boolean;
    is_default: boolean;
    questions: Prompt[];
}

export type SessionPrompts = Record<string, PromptCategory[]>;

export interface PlayBook {
    id: string;
    name: string;
    when_to_use: string;
    what_to_do: string;
    enabled: boolean;
}

export interface LLMParameters {
    temperature: number;
    reasoning_effort: string;
    top_p: number;
    frequency_penalty: number;
    presence_penalty: number;
}

export interface LLMConfig {
    model: string;
    parameters: LLMParameters;
}

export interface ConfigPayload {
    config_values: Record<string, any>;
    config_schema: Record<string, any>;
}

export enum ToolApprovalState {
    ASK = "ask",
    DENY = "deny",
    ALLOW = "allow"
}

export interface MCPTool {
    name: string;
    description: string;
    inputSchema: Record<string, any>;
    server_label: string;
    approval: ToolApprovalState;
}

// --- Container Models ---
export interface Container {
    containerId: string;
    image: ContainerImage;
    arguments: Record<string, any>;
    agents: ContainerAgent[];
    owner: string;
    runningSince: string;
    connectivity: ContainerConnectivity | null;
    approvals?: Record<string, ToolApprovalState>; // UI internal field, not returned by backend
}

export interface ContainerImage {
    imageName: string;
    requires: string[];
    provides: string[];
    url: string | null;
    name: string | null;
    description: string | null;
    version: string | null;
    provider: string | null;
    apiPort: number;
    extraPorts: Record<number, PortMapping>;
    parameters: ContainerParameter[];
    definitions: Record<string, any>;
    defintionsByUrl: Record<string, string>;
}

export interface ContainerParameter {
    name: string;
    type: string;
    required: boolean;
    confidential: boolean;
    defaultValue?: any;
}

export interface ContainerAction {
    name: string;
    description: string | null;
    parameters: Record<string, any>;
    result?: any;
    callback?: any
}

export interface ContainerStream {
    name: string;
    description?: string;
    mode: "GET" | "POST";
    callback?: any;
}

export interface ContainerAgent {
    agentId: string;
    agentType: string;
    description?: string;
    actions: ContainerAction[];
    streams: ContainerStream[];
}

export interface PortMapping {
    protocol: string;
    description: string;
}

export interface ContainerConnectivity {
    publicUrl: string;
    apiPortMapping: number;
    extraPortMappings: Record<string, PortMapping>;
}

export interface PostContainerRequest {
    image: ContainerImage;
    arguments?: Record<string, any>;
}

export interface PostContainerResponse {
    success: boolean;
    error?: string;
}

export interface ExtraPortEndpoint {
    fullUrl: string;
    description: string;
}

export interface ContainerExtraPorts {
    container: string;
    extraPorts: ExtraPortEndpoint[];
}
