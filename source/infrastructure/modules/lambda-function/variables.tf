variable "name" {
  description = "Function name."
  type        = string
}

variable "handler" {
  description = "Python handler path, e.g. handlers.list_tasks.handler."
  type        = string
}

variable "package_path" {
  description = "Path to the deployment zip built by deployment/build-dist.sh."
  type        = string
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "architecture" {
  type    = string
  default = "arm64"
}

variable "memory_size" {
  type = number
}

variable "timeout" {
  type = number
}

variable "environment" {
  description = "Environment variables for the function."
  type        = map(string)
  default     = {}
}

variable "layers" {
  type    = list(string)
  default = []
}

variable "log_retention_days" {
  type = number
}

variable "policy_statements" {
  description = "IAM statements granting exactly the AWS calls this function makes."
  type = list(object({
    actions   = list(string)
    resources = list(string)
  }))
}
