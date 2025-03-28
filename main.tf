
resource "aws_instance" "CWAgent" {
  instance_type     = "t2.micro"
  key_name          = "key100"
  ami               = "ami-0e5c9f1cb7457e5dd"
  availability_zone = "ap-southeast-2a"
  subnet_id         = "subnet-0b9f0ceafab4f955e"
  associate_public_ip_address = "true"
  security_groups   = ["sg-04e757f5e14427f2c"]
  iam_instance_profile = "CloudWatchAgentServerRole"
   user_data = file("/Users/rehmatou/Documents/Terraform/EC2-CW-Agent/userdata.sh")

  tags = {
    Name = "CloudwatchAgent-Single"
  }

}
