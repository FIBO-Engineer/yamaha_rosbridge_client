#!/usr/bin/python3

import rospy
import roslibpy
from autoware_msgs.msg import VehicleCmd
import time

class RosBridgeConnector():
    def __init__(self):
        rospy.init_node('yamaha_rosbridge_client')
        self.subscriber = rospy.Subscriber('/vehicle_cmd', VehicleCmd, self.vehicle_cmd_callback, queue_size=5)
        self.host = rospy.get_param("~host", "127.0.0.1")
        self.port = rospy.get_param("~port", "9090")
        self.reconnection_period = rospy.get_param("~reconnection_period", 1)
        self.client = roslibpy.Ros(host=self.host, port=self.port)
        self.publisher = roslibpy.Topic(self.client, "/nav_vel", "geometry_msgs/TwistStamped")
        self.timestamp = 0

    def connect_to_server(self):
        try:
            self.client.run()
            rospy.loginfo("Connected to server")
        except Exception as e:
            rospy.logerr("Cannot connect to server! and the error is %s", e)

    def advertise_topic(self):
        try:
            if self.client.is_connected:
                self.publisher.advertise()
                rospy.loginfo("Advertised the topic")
            else:
                rospy.logerr("Cannot connect to server and cannot advertise the topic!")
        except Exception as e:
            rospy.logerr("Cannot advertise the topic! and the error is %s", e)

    def un_advertise_topic(self):
        try:
            if self.client.is_connected:
                self.publisher.unadvertise()
                rospy.loginfo("Unadvertised the topic")
            else:
                rospy.logerr("Cannot connect to server and cannot unadvertise the topic!")
        except Exception as e:
            rospy.logerr("Cannot unadvertise the topic! and the error is %s", e)
    
    def exit_from_the_server(self):
        try:    
            self.client.terminate()
            rospy.loginfo("Exited from the server")
        except Exception as e:
            rospy.logerr("Cannot exit from the server! and the error is %s", e)

    def vehicle_cmd_callback(self, data):
        try:
            if self.client.is_connected:
                pub_message = roslibpy.Message(
                    {
                        "header": {
                            "stamp": {
                                "secs": data.header.stamp.secs,
                                "nsecs": data.header.stamp.nsecs
                            },
                            "frame_id": data.header.frame_id
                        },
                        "twist": {
                            "linear": {
                                "x": data.twist_cmd.twist.linear.x,
                                "y": data.twist_cmd.twist.linear.y,
                                "z": data.twist_cmd.twist.linear.z
                            },
                            "angular": {
                                "x": data.twist_cmd.twist.angular.x,
                                "y": data.twist_cmd.twist.angular.y,
                                "z": data.twist_cmd.twist.angular.z
                            }
                        }
                    }
                )
                self.publisher.publish(pub_message)
                rospy.loginfo("Published message to the topic")
            else:
                rospy.logerr("Cannot connect to server!")
        except Exception as e:
            rospy.logerr("Cannot publish message to the topic! and the error is %s", e)

    def process_handling(self):
        if time.time() - self.timestamp > self.reconnection_period: 
            if not self.client.is_connected:
                rospy.logwarn("Cannot connect to the server! and Retry to connect and advertise topic to the server")
                self.connect_to_server()
                self.advertise_topic()
            self.timestamp = time.time()

def main():
    init = RosBridgeConnector()
    init.connect_to_server()
    init.advertise_topic()
    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        init.process_handling()
        rate.sleep()
    init.un_advertise_topic()
    init.exit_from_the_server()
    
if __name__ == '__main__':
    main()