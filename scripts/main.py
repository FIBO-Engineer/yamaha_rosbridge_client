#!/usr/bin/python3

import rospy
from autoware_msgs.msg import VehicleCmd
import websockets
import asyncio
import json

class Ros1ToRos2():
    def __init__(self):
        rospy.init_node('yamaha_rosbridge_client')
        self.uri = rospy.get_param("~uri")
        self.advertise_msg = dict()
        self.publish_msg = dict()
        self.subscriber = rospy.Subscriber('/vehicle_cmd', VehicleCmd, self.callback, queue_size=5)
        self.is_call_publish_to_websocket = False
        self.is_advertise_initial = False

    def callback(self, data):
        self.publish_msg = {
            "op": "publish",
            "topic": "/nav_vel",
            "msg": {
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
        }
        self.is_call_publish_to_websocket = True

    async def advertise_and_publish_to_websocket(self):
        self.advertise_msg = {
            "op": "advertise",
            "topic": "/nav_vel",
            "type": "geometry_msgs/TwistStamped"
        }
        try:
            async with websockets.connect(self.uri) as websocket:
                await websocket.send(json.dumps(self.advertise_msg))
                if not self.is_advertise_initial:
                    rospy.loginfo("Advertise the topic!")
                    self.is_advertise_initial = True
                if self.is_call_publish_to_websocket:
                    await websocket.send(json.dumps(self.publish_msg))
                    rospy.loginfo("Publish data!")
                    self.is_call_publish_to_websocket = False

        except Exception as e:
            rospy.logerr("Error: %s", e)

    def handling(self):
        asyncio.get_event_loop().run_until_complete(self.advertise_and_publish_to_websocket())  

def main():
    init = Ros1ToRos2()
    loop_sleep_rate = rospy.get_param("~loop_sleep_rate")
    rate = rospy.Rate(loop_sleep_rate)
    while not rospy.is_shutdown():
        init.handling()
        rate.sleep()

if __name__ == '__main__':
    main()
