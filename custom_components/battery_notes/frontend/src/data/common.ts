export interface Route {
  path: string;
  prefix: string;
}

export interface Critical {
  repository: string;
  reason: string;
  link: string;
  acknowledged: boolean;
}

export interface Configuration {
  categories: [string];
  country: string;
  debug: boolean;
  dev: string;
  experimental: boolean;
  frontend_compact: boolean;
  frontend_expected: string;
  frontend_mode: string;
  frontend_running: string;
  onboarding_done: boolean;
  version: string;
}

export interface Status {
  background_task: boolean;
  disabled: boolean;
  disabled_reason?: string;
  lovelace_mode: "storage" | "yaml" | "auto-gen";
  stage: "startup" | "waiting" | "running" | "setup";
  reloading_data: boolean;
  startup: boolean;
  manage_mode: boolean;
  upgrading_all: boolean;
  has_pending_tasks: boolean;
}

export interface LovelaceResource {
  type: "css" | "js" | "module" | "html";
  url: string;
  id: number;
}

export interface LovelaceResourcesMutableParams {
  resource_id?: number;
  res_type: "css" | "js" | "module" | "html";
  url: string;
}

export interface Message {
  name: string;
  info: string;
  secondary?: string;
  severity?: "info" | "warning" | "error" | "success";
  path?: string;
  iconPath?: string;
  dialog?: string;
  repository?: Repository;
}

export interface LocationChangedEvent {
  detail?: { route: Route; force?: boolean };
}

export interface insteonDialogEvent {
  detail?: {
    type: string;
    header?: string;
    content?: string;
    markdown?: boolean;
    frosen?: boolean;
    repository?: Repository;
  };
}

export interface Repository {
  has_icon_url: boolean;
  additional_info: string;
  authors: [string];
  available_version: string;
  beta: boolean;
  can_install: boolean;
  category: string;
  config_flow: boolean;
  country: string;
  custom: boolean;
  default_branch: string;
  description: string;
  domain: string;
  downloads: number;
  file_name: string;
  first_install: boolean;
  full_name: string;
  hide: boolean;
  hide_default_branch: boolean;
  homeassistant: string;
  id: string;
  info: string;
  installed_version: string;
  installed: boolean;
  issues: number;
  javascript_type: string;
  last_updated: string;
  local_path: string;
  main_action: string;
  name: string;
  new: string;
  pending_upgrade: boolean;
  releases: [string];
  selected_tag: string;
  stars: number;
  state: string;
  status_description: string;
  status: string;
  topics: [string];
  updated_info: boolean;
  version_or_commit: string;
}

export interface RemovedRepository {
  link?: string;
  reason?: string;
  removal_type: string;
  repository: string;
}

export interface Filter {
  id: string;
  value: string;
  checked?: boolean;
}

export const sortRepositoriesByName = (
  repositories: Repository[],
): Repository[] =>
  repositories?.sort((a: Repository, b: Repository) =>
    a.name.toLowerCase() > b.name.toLowerCase() ? 1 : -1,
  );
