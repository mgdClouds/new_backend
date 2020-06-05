DROP TRIGGER IF EXISTS `tri_update_engineer`;
DELIMITER ;;
CREATE TRIGGER `tri_update_engineer` AFTER UPDATE ON `user` FOR EACH ROW begin
    if new.role = "engineer" then
        update career set real_name=new.real_name, phone=new.phone where engineer_id=new.id;
    end if;
end
;;

CREATE TRIGGER `tri_update_daily_log` AFTER UPDATE ON `daily_log` FOR EACH ROW begin
    set new.absent_time =  new.duration + new.leave_time + new.shift_time - 8
end
;;

DELIMITER ;
