export enum DurationType {
    DAYS = "days",
    WEEKS = "weeks",
    MONTHS = "months",
    YEARS = "years"
}

export interface Status {
    id: number;
    name: string;
    code: string;
    color: string;
    order: number;
    is_active: boolean;
    is_default: boolean;
    is_final: boolean;
}

export interface Priority {
    id: number;
    name: string;
    color: string;
    order: number;
    is_active: boolean;
    is_default: boolean;
}

export interface Duration {
    id: number;
    name: string;
    type: DurationType;
    value: number;
    is_active: boolean;
    is_default: boolean;
}

export interface Task {
    id: number;
    title: string;
    description: string | null;
    status: Status | null;
    priority: Priority | null;
    duration: Duration | null;
    deadline: string | null;
    created_at: string;
    completed_at: string | null;
    is_overdue: boolean;
    reminders: string[];
    tags: string[];
    custom_fields: Record<string, any>;
}

export interface Settings {
    statuses: Status[];
    priorities: Priority[];
    durations: Duration[];
} 