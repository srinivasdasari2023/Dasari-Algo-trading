# Dev environment – minimal skeleton
# Use modules for network, database, cache, compute
terraform {
  required_version = ">= 1.5"
  backend "s3" {
    # Configure per env: bucket, key, region
    # key = "capitalguard/dev/terraform.tfstate"
  }
}

# module "network" { source = "../../modules/network" ...
# module "database" { source = "../../modules/database" ...
# module "cache" { source = "../../modules/cache" ...
